#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "libretro.h"
#include "snes9x.h"
#include "memmap.h"
#include "cpuexec.h"

#define RECORD_BYTES 12

static FILE *trace_out = NULL;
static unsigned long port_accesses = 0;
static unsigned long frames_seen = 0;
static unsigned pad_state = 0;

static unsigned frame_width = 0;
static unsigned frame_height = 0;
static unsigned frame_pitch = 0;
static std::vector<uint16_t> frame;
static unsigned long frames_delivered = 0;

struct Press {
    unsigned long at_frame;
    unsigned buttons;
};
static std::vector<Press> script;
static size_t script_at = 0;

static void put_u32(unsigned char *at, unsigned long value)
{
    at[0] = (unsigned char)(value & 0xFF);
    at[1] = (unsigned char)((value >> 8) & 0xFF);
    at[2] = (unsigned char)((value >> 16) & 0xFF);
    at[3] = (unsigned char)((value >> 24) & 0xFF);
}

static void put_u16(unsigned char *at, unsigned value)
{
    at[0] = (unsigned char)(value & 0xFF);
    at[1] = (unsigned char)((value >> 8) & 0xFF);
}

extern "C" void pw_note_dsp(int is_read, unsigned char byte, unsigned short address)
{
    port_accesses++;
    if (!trace_out) {
        return;
    }
    unsigned char record[RECORD_BYTES];
    memset(record, 0, sizeof(record));
    put_u32(record + 0, frames_seen);
    put_u32(record + 4, (unsigned long)Registers.PBPC);
    put_u16(record + 8, address);
    record[10] = (unsigned char)(is_read ? 1 : 0);
    record[11] = byte;
    fwrite(record, 1, sizeof(record), trace_out);
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
    if (size <= 0) {
        fclose(in);
        return false;
    }
    into.resize((size_t)size);
    const size_t got = fread(into.data(), 1, into.size(), in);
    fclose(in);
    return got == into.size();
}

static unsigned button_named(const std::string &name)
{
    if (name == "up") return 1u << RETRO_DEVICE_ID_JOYPAD_UP;
    if (name == "down") return 1u << RETRO_DEVICE_ID_JOYPAD_DOWN;
    if (name == "left") return 1u << RETRO_DEVICE_ID_JOYPAD_LEFT;
    if (name == "right") return 1u << RETRO_DEVICE_ID_JOYPAD_RIGHT;
    if (name == "a") return 1u << RETRO_DEVICE_ID_JOYPAD_A;
    if (name == "b") return 1u << RETRO_DEVICE_ID_JOYPAD_B;
    if (name == "x") return 1u << RETRO_DEVICE_ID_JOYPAD_X;
    if (name == "y") return 1u << RETRO_DEVICE_ID_JOYPAD_Y;
    if (name == "l") return 1u << RETRO_DEVICE_ID_JOYPAD_L;
    if (name == "r") return 1u << RETRO_DEVICE_ID_JOYPAD_R;
    if (name == "start") return 1u << RETRO_DEVICE_ID_JOYPAD_START;
    if (name == "select") return 1u << RETRO_DEVICE_ID_JOYPAD_SELECT;
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
        while (*cursor == ' ' || *cursor == '\t') {
            cursor++;
        }
        if (*cursor == '#' || *cursor == '\n' || *cursor == '\0') {
            continue;
        }
        Press press;
        press.at_frame = strtoul(cursor, &cursor, 10);
        press.buttons = 0;
        while (*cursor) {
            while (*cursor == ' ' || *cursor == '\t') {
                cursor++;
            }
            char name[32];
            int at = 0;
            while (*cursor && *cursor != ' ' && *cursor != '\t' && *cursor != '\n' &&
                   at < (int)sizeof(name) - 1) {
                name[at++] = *cursor++;
            }
            name[at] = '\0';
            if (at) {
                press.buttons |= button_named(name);
            }
            if (*cursor == '\n' || *cursor == '\0') {
                break;
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

static double frame_brightness(void)
{
    if (frame.empty() || frame_width == 0) {
        return -1.0;
    }
    double total = 0.0;
    for (unsigned y = 0; y < frame_height; y++) {
        for (unsigned x = 0; x < frame_width; x++) {
            const uint16_t pixel = frame[y * frame_pitch + x];
            total += ((pixel >> 11) & 0x1F) * 8 + ((pixel >> 5) & 0x3F) * 4 + (pixel & 0x1F) * 8;
        }
    }
    return total / (double)(frame_width * frame_height * 3);
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: pwemu <rom> <frames>\n");
        fprintf(stderr, "  PWTRACE=<path>   binary coprocessor port log\n");
        fprintf(stderr, "  PWSCRIPT=<path>  input script, one 'frame button...' per line\n");
        return 2;
    }

    const unsigned long frames_to_run = strtoul(argv[2], NULL, 10);

    std::vector<unsigned char> rom;
    if (!read_file(argv[1], rom)) {
        fprintf(stderr, "cannot read %s\n", argv[1]);
        return 1;
    }

    const char *trace_path = getenv("PWTRACE");
    if (trace_path) {
        trace_out = fopen(trace_path, "wb");
        if (!trace_out) {
            fprintf(stderr, "cannot write %s\n", trace_path);
            return 1;
        }
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
    info.path = argv[1];
    info.data = rom.data();
    info.size = rom.size();

    if (!retro_load_game(&info)) {
        printf("RESULT load=failed\n");
        return 1;
    }

    for (unsigned long at = 0; at < frames_to_run; at++) {
        frames_seen = at;
        apply_script(at);
        retro_run();
    }

    if (trace_out) {
        fclose(trace_out);
    }

    printf("RESULT load=ok frames=%lu delivered=%lu accesses=%lu brightness=%.2f\n",
           frames_to_run, frames_delivered, port_accesses, frame_brightness());

    retro_unload_game();
    retro_deinit();
    return 0;
}
