/* One native synthetic runtime for raw isolation probes and bounded cases. */
#include <stdio.h>
#include <string.h>

/* Reuse the audited operation implementation; only dispatch differs here. */
#define main aegis_feasibility_probe_main
#include "seatbelt_feasibility_probe.c"
#undef main

static const char abstain[] =
    "{\"activity_relation\":\"unclear\",\"anonymous_participant_configuration\":\"unclear\","
    "\"capture_or_projection_artifact\":\"unclear\",\"early_state_coherence\":\"unclear\","
    "\"exposure_or_palette_change\":\"unclear\",\"foreground_rearrangement\":\"unclear\","
    "\"late_state_coherence\":\"unclear\",\"setting_relation\":\"unclear\","
    "\"status\":\"abstain\",\"transition_support\":\"insufficient\","
    "\"viewpoint_change\":\"unclear\"}";

static int emit_case_bytes(const char *bytes, size_t length) {
    return fwrite(bytes, 1, length, stdout) == length ? 0 : 74;
}

int main(int argc, char **argv) {
    if (argc == 20 && strcmp(argv[1], "--aegis-isolation-probe") == 0) {
        char *translated[21];
        for (int i = 0; i < argc; ++i) translated[i] = argv[i];
        translated[1] = "--aegis-seatbelt-feasibility-probe";
        translated[argc] = NULL;
        return aegis_feasibility_probe_main(argc, translated);
    }
    if (argc >= 4 && strcmp(argv[1], "--aegis-synthetic-case") == 0 &&
            strcmp(argv[3], "--") == 0) {
        const char *case_id = argv[2];
        if (strcmp(case_id, "argv_literal") == 0 && argc == 6 &&
                strcmp(argv[4], ";$(touch should-not-run)") == 0 &&
                strcmp(argv[5], "* ' \" \\") == 0)
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        if (argc != 4) return 64;
        if (strcmp(case_id, "stdout_empty") == 0) return 0;
        if (strcmp(case_id, "stdout_invalid_utf8") == 0) {
            static const char invalid[] = "\xff";
            return emit_case_bytes(invalid, sizeof(invalid) - 1U);
        }
        if (strcmp(case_id, "stdout_duplicate_key") == 0) {
            static const char duplicate[] = "{\"status\":\"abstain\",\"status\":\"abstain\"}";
            return emit_case_bytes(duplicate, sizeof(duplicate) - 1U);
        }
        if (strcmp(case_id, "stdout_nan") == 0) {
            static const char nan_value[] = "{\"status\":NaN}";
            return emit_case_bytes(nan_value, sizeof(nan_value) - 1U);
        }
        if (strcmp(case_id, "stdout_trailing_bytes") == 0) {
            static const char trailing[] = "{}{}";
            return emit_case_bytes(trailing, sizeof(trailing) - 1U);
        }
        if (strcmp(case_id, "stdout_forbidden_field") == 0) {
            static const char forbidden[] = "{\"source_time\":0}";
            return emit_case_bytes(forbidden, sizeof(forbidden) - 1U);
        }
        if (strcmp(case_id, "stdout_extra_field") == 0) {
            static const char extra[] = "{\"unexpected\":true}";
            return emit_case_bytes(extra, sizeof(extra) - 1U);
        }
    }
    return 64;
}
