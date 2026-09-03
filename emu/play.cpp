#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include <dlfcn.h>
#include <SDL.h>

#include "libretro.h"

static const int SCREEN_WIDTH = 256;
static const int SCREEN_HEIGHT = 224;
static const int DEFAULT_SCALE = 3;

static SDL_Window *window = NULL;
static SDL_Renderer *renderer = NULL;
static SDL_Texture *texture = NULL;

static unsigned pad_state = 0;

struct Binding {
    SDL_Keycode key;
    unsigned bit;
};

static const Binding BINDINGS[] = {
    {SDLK_x, 1u << 0},      {SDLK_z, 1u << 1},     {SDLK_RSHIFT, 1u << 2},
    {SDLK_RETURN, 1u << 3}, {SDLK_UP, 1u << 4},    {SDLK_DOWN, 1u << 5},
    {SDLK_LEFT, 1u << 6},   {SDLK_RIGHT, 1u << 7}, {SDLK_s, 1u << 8},
    {SDLK_a, 1u << 9},      {SDLK_q, 1u << 10},    {SDLK_w, 1u << 11},
};

static void cb_video(const void *data, unsigned width, unsigned height, size_t pitch)
{
    if (!data || !texture) {
        return;
    }
    SDL_UpdateTexture(texture, NULL, data, (int)pitch);
    SDL_RenderClear(renderer);
    SDL_Rect from = {0, 0, (int)width, (int)height};
    SDL_RenderCopy(renderer, texture, &from, NULL);
    SDL_RenderPresent(renderer);
}

static void cb_audio(int16_t, int16_t) {}

static size_t cb_audio_batch(const int16_t *, size_t frames_count)
{
    return frames_count;
}

static void cb_input_poll(void) {}

static int16_t cb_input_state(unsigned port, unsigned, unsigned, unsigned id)
{
    if (port != 0 || id > 15) {
        return 0;
    }
    return (pad_state >> id) & 1;
}

static bool cb_environment(unsigned cmd, void *data)
{
    switch (cmd) {
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
    case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
        *(const char **)data = ".";
        return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
    case RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL:
    case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
    case RETRO_ENVIRONMENT_SET_VARIABLES:
    case RETRO_ENVIRONMENT_SET_MEMORY_MAPS:
    case RETRO_ENVIRONMENT_SET_GEOMETRY:
    case RETRO_ENVIRONMENT_SET_SUPPORT_ACHIEVEMENTS:
        return true;
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE:
        *(bool *)data = false;
        return true;
    default:
        return false;
    }
}

static bool read_file(const char *path, std::vector<unsigned char> &into)
{
    FILE *in = fopen(path, "rb");
    if (!in) {
        return false;
    }
    fseek(in, 0, SEEK_END);
    const long size = ftell(in);
    fseek(in, 0, SEEK_SET);
    into.resize((size_t)size);
    const size_t got = fread(into.data(), 1, into.size(), in);
    fclose(in);
    return got == into.size();
}

static void apply_key(SDL_Keycode key, bool down)
{
    for (unsigned at = 0; at < sizeof(BINDINGS) / sizeof(BINDINGS[0]); at++) {
        if (BINDINGS[at].key == key) {
            if (down) {
                pad_state |= BINDINGS[at].bit;
            } else {
                pad_state &= ~BINDINGS[at].bit;
            }
        }
    }
}

#define BIND(name)                                                                                 \
    auto name = (decltype(::name) *)dlsym(core, #name);                                            \
    if (!name) {                                                                                   \
        fprintf(stderr, "core has no %s\n", #name);                                                \
        return 1;                                                                                  \
    }

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: play <core.dylib> <rom>\n");
        fprintf(stderr, "  arrows move, Z and X and A and S are the face buttons,\n");
        fprintf(stderr, "  Q and W are the shoulders, Return starts, Right Shift selects,\n");
        fprintf(stderr, "  Escape quits\n");
        return 2;
    }

    void *core = dlopen(argv[1], RTLD_NOW);
    if (!core) {
        fprintf(stderr, "cannot load %s: %s\n", argv[1], dlerror());
        return 1;
    }

    BIND(retro_set_environment)
    BIND(retro_set_video_refresh)
    BIND(retro_set_audio_sample)
    BIND(retro_set_audio_sample_batch)
    BIND(retro_set_input_poll)
    BIND(retro_set_input_state)
    BIND(retro_init)
    BIND(retro_load_game)
    BIND(retro_run)
    BIND(retro_unload_game)
    BIND(retro_deinit)

    std::vector<unsigned char> rom;
    if (!read_file(argv[2], rom)) {
        fprintf(stderr, "cannot read %s\n", argv[2]);
        return 1;
    }

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }
    window = SDL_CreateWindow(argv[2], SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              SCREEN_WIDTH * DEFAULT_SCALE, SCREEN_HEIGHT * DEFAULT_SCALE,
                              SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGB565, SDL_TEXTUREACCESS_STREAMING,
                                SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2);
    if (!window || !renderer || !texture) {
        fprintf(stderr, "SDL: %s\n", SDL_GetError());
        return 1;
    }

    retro_set_environment(cb_environment);
    retro_set_video_refresh(cb_video);
    retro_set_audio_sample(cb_audio);
    retro_set_audio_sample_batch(cb_audio_batch);
    retro_set_input_poll(cb_input_poll);
    retro_set_input_state(cb_input_state);
    retro_init();

    retro_game_info info;
    memset(&info, 0, sizeof(info));
    info.path = argv[2];
    info.data = rom.data();
    info.size = rom.size();

    if (!retro_load_game(&info)) {
        fprintf(stderr, "the core refused this image\n");
        return 1;
    }

    bool running = true;
    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            } else if (event.type == SDL_KEYDOWN || event.type == SDL_KEYUP) {
                if (event.key.keysym.sym == SDLK_ESCAPE) {
                    running = false;
                }
                apply_key(event.key.keysym.sym, event.type == SDL_KEYDOWN);
            }
        }
        retro_run();
    }

    retro_unload_game();
    retro_deinit();
    SDL_DestroyTexture(texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
