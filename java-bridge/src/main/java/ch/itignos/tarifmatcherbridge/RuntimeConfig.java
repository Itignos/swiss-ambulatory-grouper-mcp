package ch.itignos.tarifmatcherbridge;

import java.nio.file.Path;

public record RuntimeConfig(
        Path jarPath,
        Path dataDir,
        String tariffYear,
        String icdYear
) {
    public static RuntimeConfig fromEnv() {
        return new RuntimeConfig(
                Path.of(System.getenv().getOrDefault("TARIFMATCHER_JAR", "/data/runtime/tarifmatcher/current/tarifmatcher-standalone.jar")),
                Path.of(System.getenv().getOrDefault("TARIFMATCHER_DATA_DIR", "/data/runtime/tarifmatcher/current")),
                System.getenv().getOrDefault("TARIFMATCHER_TARIFF_YEAR", "2027"),
                System.getenv().getOrDefault("TARIFMATCHER_ICD_YEAR", "2026")
        );
    }
}
