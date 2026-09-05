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

static const char *shot_dir = NULL;
static std::vector<unsigned long> shot_frames;
static unsigned long frame_number = 0;

static void write_shot(const char *path)
{
    if (frame.empty() || frame_width == 0) {
        return;
    }
    FILE *out = fopen(path, "wb");
    if (!out) {
        return;
    }
    fprintf(out, "P6\n%u %u\n255\n", frame_width, frame_height);
    for (unsigned y = 0; y < frame_height; y++) {
        for (unsigned x = 0; x < frame_width; x++) {
            const uint16_t pixel = frame[y * frame_pitch + x];
            const unsigned char rgb[3] = {
                (unsigned char)(((pixel >> 11) & 0x1F) * 255 / 31),
                (unsigned char)(((pixel >> 5) & 0x3F) * 255 / 63),
                (unsigned char)((pixel & 0x1F) * 255 / 31),
            };
            fwrite(rgb, 1, 3, out);
        }
    }
    fclose(out);
}

static const char *wram_dir = NULL;
static void *(*get_memory)(unsigned) = NULL;
static size_t (*get_memory_size)(unsigned) = NULL;

static void maybe_dump_wram(void)
{
    if (!wram_dir || !get_memory) {
        return;
    }
    void *ram = get_memory(RETRO_MEMORY_SYSTEM_RAM);
    const size_t span = get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
    if (!ram || !span) {
        return;
    }
    char path[512];
    snprintf(path, sizeof(path), "%s/wram-%06lu.bin", wram_dir, frame_number);
    FILE *out = fopen(path, "wb");
    if (!out) {
        return;
    }
    fwrite(ram, 1, span, out);
    fclose(out);

    void *vram = get_memory(RETRO_MEMORY_VIDEO_RAM);
    const size_t vspan = get_memory_size(RETRO_MEMORY_VIDEO_RAM);
    if (!vram || !vspan) {
        return;
    }
    snprintf(path, sizeof(path), "%s/vram-%06lu.bin", wram_dir, frame_number);
    out = fopen(path, "wb");
    if (!out) {
        return;
    }
    fwrite(vram, 1, vspan, out);
    fclose(out);
}

static long tick_at = -1;
static unsigned long tick_from = 0;
static unsigned long tick_to = 0;
static long tick_last = -1;
static std::vector<uint16_t> held_frame;
static unsigned held_width = 0;
static unsigned held_height = 0;
static unsigned held_pitch = 0;
static std::vector<unsigned char> held_ram;
static unsigned long tick_after = 0;
static unsigned long tick_countdown = 0;
static long tick_pending = -1;

static void write_held(unsigned long tick)
{
    char path[512];
    if (shot_dir) {
        snprintf(path, sizeof(path), "%s/frame-%06lu.ppm", shot_dir, tick);
        write_shot(path);
    }
    if (wram_dir && get_memory) {
        void *vram = get_memory(RETRO_MEMORY_VIDEO_RAM);
        const size_t span = get_memory_size(RETRO_MEMORY_VIDEO_RAM);
        if (vram && span) {
            snprintf(path, sizeof(path), "%s/vram-%06lu.bin", wram_dir, tick);
            FILE *out = fopen(path, "wb");
            if (out) {
                fwrite(vram, 1, span, out);
                fclose(out);
            }
        }
    }
    if (wram_dir && !held_ram.empty()) {
        snprintf(path, sizeof(path), "%s/wram-%06lu.bin", wram_dir, tick);
        FILE *out = fopen(path, "wb");
        if (out) {
            fwrite(held_ram.data(), 1, held_ram.size(), out);
            fclose(out);
        }
    }
}

static long rate_at = -1;
static unsigned long rate_from = 0;
static unsigned long rate_to = 0;
static long rate_last = -1;
static unsigned long rate_first = 0;
static unsigned long rate_first_console = 0;
static unsigned long rate_reported = 0;
static unsigned long rate_first_idle = 0;

static void maybe_note_rate(void)
{
    if (rate_at < 0 || !get_memory || rate_reported) {
        return;
    }
    const unsigned char *ram = (const unsigned char *)get_memory(RETRO_MEMORY_SYSTEM_RAM);
    const size_t span = get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
    if (!ram || span < (size_t)rate_at + 2) {
        return;
    }
    const unsigned long tick = ram[rate_at] | ram[rate_at + 1] << 8;
    if ((long)tick == rate_last) {
        return;
    }
    rate_last = (long)tick;
    if (tick >= rate_from && rate_first_console == 0) {
        rate_first = tick;
        rate_first_console = frame_number;
        rate_first_idle = (unsigned long)(ram[0x19A00] | ram[0x19A01] << 8 | ram[0x19A02] << 16 |
                                          (unsigned long)ram[0x19A03] << 24);
        return;
    }
    if (tick >= rate_to && rate_first_console != 0) {
        rate_reported = 1;
        printf("RATE from=%lu at=%lu to=%lu at=%lu frames=%.4f idle=%lu\n", rate_first,
               rate_first_console, tick, frame_number,
               (double)(frame_number - rate_first_console) / (double)(tick - rate_first),
               (unsigned long)(ram[0x19A00] | ram[0x19A01] << 8 | ram[0x19A02] << 16 |
                               (unsigned long)ram[0x19A03] << 24) -
                   rate_first_idle);
    }
}

static void maybe_shoot_tick(void)
{
    if (tick_at < 0 || !get_memory) {
        return;
    }
    const unsigned char *ram = (const unsigned char *)get_memory(RETRO_MEMORY_SYSTEM_RAM);
    const size_t span = get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
    if (!ram || span < (size_t)tick_at + 2) {
        return;
    }
    const unsigned long tick = ram[tick_at] | ram[tick_at + 1] << 8;
    if (tick_after && tick_pending >= 0) {
        if (tick_countdown == 0) {
            held_frame = frame;
            held_width = frame_width;
            held_height = frame_height;
            held_pitch = frame_pitch;
            held_ram.assign(ram, ram + span);
            write_held((unsigned long)tick_pending);
            tick_pending = -1;
        } else {
            tick_countdown--;
        }
    }
    if ((long)tick != tick_last) {
        if (tick_last >= 0 && (unsigned long)tick_last >= tick_from &&
            (unsigned long)tick_last <= tick_to) {
            if (tick_after) {
                tick_pending = tick_last;
                tick_countdown = tick_after;
            } else {
                write_held((unsigned long)tick_last);
            }
        }
        tick_last = (long)tick;
    }
    if (tick_after) {
        return;
    }
    held_frame = frame;
    held_width = frame_width;
    held_height = frame_height;
    held_pitch = frame_pitch;
    held_ram.assign(ram, ram + span);
}

static void write_memory_at_console_frame(void)
{
    if (!wram_dir || !get_memory) {
        return;
    }
    char path[512];
    const unsigned char *ram = (const unsigned char *)get_memory(RETRO_MEMORY_SYSTEM_RAM);
    const size_t span = get_memory_size(RETRO_MEMORY_SYSTEM_RAM);
    if (ram && span) {
        snprintf(path, sizeof(path), "%s/wram-%06lu.bin", wram_dir, frame_number);
        FILE *out = fopen(path, "wb");
        if (out) {
            fwrite(ram, 1, span, out);
            fclose(out);
        }
    }
    void *vram = get_memory(RETRO_MEMORY_VIDEO_RAM);
    const size_t vspan = get_memory_size(RETRO_MEMORY_VIDEO_RAM);
    if (vram && vspan) {
        snprintf(path, sizeof(path), "%s/vram-%06lu.bin", wram_dir, frame_number);
        FILE *out = fopen(path, "wb");
        if (out) {
            fwrite(vram, 1, vspan, out);
            fclose(out);
        }
    }
}

static void maybe_shoot(void)
{
    int listed = 0;
    for (size_t at = 0; at < shot_frames.size(); at++) {
        if (shot_frames[at] == frame_number) {
            listed = 1;
            break;
        }
    }
    if (!listed) {
        return;
    }
    if (shot_dir) {
        char path[512];
        snprintf(path, sizeof(path), "%s/frame-%06lu.ppm", shot_dir, frame_number);
        write_shot(path);
    }
    write_memory_at_console_frame();
}

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
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        struct retro_variable *asked = (struct retro_variable *)data;
        const char *chosen = getenv(asked->key);
        asked->value = chosen;
        return chosen != NULL;
    }
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

    shot_dir = getenv("PWSHOT");
    wram_dir = getenv("PWWRAM");
    get_memory = (void *(*)(unsigned))dlsym(core, "retro_get_memory_data");
    get_memory_size = (size_t (*)(unsigned))dlsym(core, "retro_get_memory_size");
    const char *shot_list = getenv("PWSHOTS");
    if (shot_list) {
        const char *cursor = shot_list;
        while (*cursor) {
            char *next = NULL;
            const unsigned long at = strtoul(cursor, &next, 10);
            if (next == cursor) {
                break;
            }
            shot_frames.push_back(at);
            cursor = (*next == ',') ? next + 1 : next;
        }
    }

    const char *rate_text = getenv("PWRATE");
    if (rate_text) {
        rate_at = (long)strtoul(rate_text, NULL, 0);
        const char *from_text = getenv("PWRATEFROM");
        const char *to_text = getenv("PWRATETO");
        rate_from = from_text ? strtoul(from_text, NULL, 0) : 250;
        rate_to = to_text ? strtoul(to_text, NULL, 0) : 500;
    }

    const char *tick_text = getenv("PWTICK");
    if (tick_text) {
        tick_at = (long)strtoul(tick_text, NULL, 0);
        const char *from_text = getenv("PWTICKFROM");
        const char *to_text = getenv("PWTICKTO");
        const char *after_text = getenv("PWTICKAFTER");
        tick_after = after_text ? strtoul(after_text, NULL, 0) : 0;
        tick_from = from_text ? strtoul(from_text, NULL, 0) : 0;
        tick_to = to_text ? strtoul(to_text, NULL, 0) : 0xFFFF;
    }

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
        frame_number = at;
        apply_script(at);
        retro_run();
        maybe_note_rate();
        maybe_shoot();
        maybe_shoot_tick();
        for (size_t k = 0; k < shot_frames.size(); k++) {
            if (shot_frames[k] == frame_number) {
                maybe_dump_wram();
            }
        }
    }

    printf("RESULT load=ok frames=%lu delivered=%lu lit=%lu brightness=%.2f\n", frames_to_run,
           frames_delivered, frames_lit,
           brightness_of(frame.data(), frame_width, frame_height, frame_pitch));

    retro_unload_game();
    retro_deinit();
    return 0;
}
