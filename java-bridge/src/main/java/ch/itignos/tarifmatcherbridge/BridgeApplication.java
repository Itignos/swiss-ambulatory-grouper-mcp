package ch.itignos.tarifmatcherbridge;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;

public final class BridgeApplication {
    private final RuntimeConfig config;
    private final TarifMatcherAdapter adapter;
    private final String adapterError;

    public BridgeApplication(RuntimeConfig config) {
        this.config = config;
        TarifMatcherAdapter loadedAdapter = null;
        String loadError = null;
        try {
            loadedAdapter = new TarifMatcherAdapter(config);
        } catch (Exception exc) {
            loadError = exc.getClass().getSimpleName() + ": " + exc.getMessage();
        }
        this.adapter = loadedAdapter;
        this.adapterError = loadError;
    }

    public static void main(String[] args) throws IOException {
        RuntimeConfig config = RuntimeConfig.fromEnv();
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8080"));
        HttpServer server = HttpServer.create(new InetSocketAddress("0.0.0.0", port), 0);
        BridgeApplication app = new BridgeApplication(config);
        server.createContext("/health", app::health);
        server.createContext("/grouper/evaluate", app::grouperEvaluate);
        server.createContext("/mapper/map", app::mapperMap);
        server.createContext("/casemaster/apply", app::casemasterApply);
        server.start();
        System.out.println("TarifMatcher bridge listening on port " + port);
    }

    private void health(HttpExchange exchange) throws IOException {
        if (!"GET".equals(exchange.getRequestMethod())) {
            send(exchange, 405, "{\"ok\":false,\"error\":\"method_not_allowed\"}");
            return;
        }
        String adapterJson;
        if (adapter == null) {
            adapterJson = "{\"loaded\":false,\"error\":\"" + escape(adapterError == null ? "unknown" : adapterError) + "\"}";
        } else {
            try {
                adapterJson = adapter.healthJson();
            } catch (Exception exc) {
                adapterJson = "{\"loaded\":false,\"error\":\"" + escape(exc.getClass().getSimpleName() + ": " + exc.getMessage()) + "\"}";
            }
        }
        String json = "{"
                + "\"ok\":" + (adapter != null) + ","
                + "\"status\":\"" + (adapter == null ? "adapter_unavailable" : "ready") + "\","
                + "\"tariff_year\":\"" + escape(config.tariffYear()) + "\","
                + "\"icd_year\":\"" + escape(config.icdYear()) + "\","
                + "\"jar\":" + fileStatus(config.jarPath()) + ","
                + "\"data_dir\":" + fileStatus(config.dataDir()) + ","
                + "\"adapter\":" + adapterJson + ","
                + "\"timestamp\":\"" + Instant.now() + "\""
                + "}";
        send(exchange, 200, json);
    }

    private void grouperEvaluate(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            send(exchange, 405, "{\"ok\":false,\"error\":\"method_not_allowed\"}");
            return;
        }
        if (adapter == null) {
            send(exchange, 503, "{\"ok\":false,\"error\":\"adapter_unavailable\",\"message\":\"" + escape(adapterError == null ? "unknown" : adapterError) + "\"}");
            return;
        }
        try {
            send(exchange, 200, adapter.evaluateGrouper(readBody(exchange)));
        } catch (Exception exc) {
            send(exchange, 500, "{\"ok\":false,\"error\":\"grouper_evaluation_failed\",\"message\":\"" + escape(exc.getClass().getSimpleName() + ": " + exc.getMessage()) + "\"}");
        }
    }

    private void mapperMap(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            send(exchange, 405, "{\"ok\":false,\"error\":\"method_not_allowed\"}");
            return;
        }
        if (adapter == null) {
            send(exchange, 503, "{\"ok\":false,\"error\":\"adapter_unavailable\",\"message\":\"" + escape(adapterError == null ? "unknown" : adapterError) + "\"}");
            return;
        }
        try {
            send(exchange, 200, adapter.evaluateMapper(readBody(exchange)));
        } catch (Exception exc) {
            send(exchange, 500, "{\"ok\":false,\"error\":\"mapper_evaluation_failed\",\"message\":\"" + escape(exc.getClass().getSimpleName() + ": " + exc.getMessage()) + "\"}");
        }
    }

    private void casemasterApply(HttpExchange exchange) throws IOException {
        handleNotImplemented(exchange, "casemaster", "casemaster_apply_not_wired");
    }

    private void handleNotImplemented(HttpExchange exchange, String component, String code) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            send(exchange, 405, "{\"ok\":false,\"error\":\"method_not_allowed\"}");
            return;
        }
        String body = readBody(exchange);
        String json = "{"
                + "\"ok\":false,"
                + "\"component\":\"" + component + "\","
                + "\"error\":\"" + code + "\","
                + "\"message\":\"OAAT TarifMatcher adapter is not wired yet; request was received by the local bridge skeleton.\","
                + "\"received_bytes\":" + body.getBytes(StandardCharsets.UTF_8).length
                + "}";
        send(exchange, 501, json);
    }

    private static String readBody(HttpExchange exchange) throws IOException {
        try (InputStream in = exchange.getRequestBody()) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static void send(HttpExchange exchange, int status, String json) throws IOException {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream out = exchange.getResponseBody()) {
            out.write(bytes);
        }
    }

    private static String fileStatus(Path path) {
        return "{"
                + "\"path\":\"" + escape(path.toString()) + "\","
                + "\"present\":" + Files.exists(path) + ","
                + "\"is_file\":" + Files.isRegularFile(path) + ","
                + "\"is_dir\":" + Files.isDirectory(path)
                + "}";
    }

    private static String escape(String input) {
        return input.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
