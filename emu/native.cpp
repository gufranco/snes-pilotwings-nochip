#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include <dlfcn.h>

#include "libretro.h"

static unsigned frame_width = 0;
static unsigned frame_height = 0;
static unsigned frame_pitch = 0;
static std::vector<uint16_t> frame;
static unsigned long frames_delivered = 0;
static unsigned long frames_lit = 0;
static const double LIT_THRESHOLD = 1.0;

static unsigned pad_state = 0;

struct Press {
    unsigned long at_frame;
    unsigned buttons;
};
static std::vector<Press> script;
static size_t script_at = 0;

static double brightness_of(const uint16_t *pixels, unsigned width, unsigned height,
                            unsigned pitch)
{
    if (!pixels || width == 0 || height == 0) {
        return 0.0;
    }
    double total = 0.0;
    for (unsigned y = 0; y < height; y++) {
        for (unsigned x = 0; x < width; x++) {
            const uint16_t pixel = pixels[y * pitch + x];
            total += ((pixel >> 11) & 0x1F) * 8 + ((pixel >> 5) & 0x3F) * 4 + (pixel & 0x1F) * 8;
        }
    }
    return total / (double)(width * height * 3);
}

static void cb_video(const void *data, unsigned width, unsigned height, size_t pitch)
{
    frames_delivered++;
    if (!data) {
        return;
    }
    frame_width = width;
    frame_height = height;
    frame_pitch = (unsigned)(pitch / sizeof(uint16_t));
    frame.assign((const uint16_t *)data, (const uint16_t *)data + frame_pitch * height);
    if (brightness_of(frame.data(), frame_width, frame_height, frame_pitch) >= LIT_THRESHOLD) {
        frames_lit++;
    }
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

static unsigned button_of(const char *name)
{
    static const char *names[] = {"b", "y", "select", "start", "up", "down",
                                  "left", "right", "a", "x", "l", "r"};
    for (unsigned at = 0; at < sizeof(names) / sizeof(names[0]); at++) {
        if (strcmp(name, names[at]) == 0) {
            return 1u << at;
        }
    }
    return 0;
}

static bool load_script(const char *path)
{
    FILE *in = fopen(path, "r");
    if (!in) {
        return false;
    }
    char line[256];
    while (fgets(line, sizeof(line), in)) {
        char *cursor = line;
        Press press;
        press.at_frame = strtoul(cursor, &cursor, 10);
        press.buttons = 0;
        while (*cursor) {
            while (*cursor == ' ' || *cursor == '\t' || *cursor == '\n') {
                cursor++;
            }
            char name[32];
            unsigned at = 0;
            while (*cursor && *cursor != ' ' && *cursor != '\t' && *cursor != '\n' &&
                   at + 1 < sizeof(name)) {
                name[at++] = *cursor++;
            }
            name[at] = '\0';
            if (at) {
                press.buttons |= button_of(name);
            }
        }
        script.push_back(press);
    }
    fclose(in);
    return true;
}

static void apply_script(unsigned long at_frame)
{
    while (script_at < script.size() && script[script_at].at_frame <= at_frame) {
        pad_state = script[script_at].buttons;
        script_at++;
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
    if (argc < 4) {
        fprintf(stderr, "usage: native <core.dylib> <rom> <frames>\n");
        fprintf(stderr, "  PWSCRIPT=<path>  input script, one 'frame button...' per line\n");
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
    const unsigned long frames_to_run = strtoul(argv[3], NULL, 10);

    const char *script_path = getenv("PWSCRIPT");
    if (script_path && !load_script(script_path)) {
        fprintf(stderr, "cannot read %s\n", script_path);
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
        printf("RESULT load=failed\n");
        return 1;
    }

    for (unsigned long at = 0; at < frames_to_run; at++) {
        apply_script(at);
        retro_run();
    }

    printf("RESULT load=ok frames=%lu delivered=%lu lit=%lu brightness=%.2f\n", frames_to_run,
           frames_delivered, frames_lit,
           brightness_of(frame.data(), frame_width, frame_height, frame_pitch));

    retro_unload_game();
    retro_deinit();
    return 0;
}
