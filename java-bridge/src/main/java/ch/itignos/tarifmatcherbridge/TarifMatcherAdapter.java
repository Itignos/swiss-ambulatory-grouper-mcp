package ch.itignos.tarifmatcherbridge;

import java.io.File;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public final class TarifMatcherAdapter {
    private final RuntimeConfig config;
    private final URLClassLoader loader;
    private final Object grouperPcs;
    private final Object capAssignmentPcs;
    private final Object catalog;
    private final Object serviceCatalog;
    private final Object tardocCatalog;
    private final Object mapper;
    private final Object gson;
    private final Path grouperSystemFile;
    private final Path capAssignmentFile;
    private final Path catalogFile;
    private final Path serviceCatalogFile;
    private final Path tardocCatalogFile;

    public TarifMatcherAdapter(RuntimeConfig config) throws Exception {
        this.config = config;
        this.loader = new URLClassLoader(new URL[]{config.jarPath().toUri().toURL()}, TarifMatcherAdapter.class.getClassLoader());
        this.gson = cls("com.google.gson.Gson").getConstructor().newInstance();
        this.grouperSystemFile = firstFile("system_ambP_*_lkaat.json");
        this.capAssignmentFile = firstFile("system_ambP_*cap_assignment.json");
        this.catalogFile = firstFile("catalog_ambP_*.csv");
        this.serviceCatalogFile = firstFile("lkaat_*.json");
        this.tardocCatalogFile = firstFile("tardoc_*_de.json");
        this.grouperPcs = readPcs(grouperSystemFile);
        this.capAssignmentPcs = capAssignmentFile == null ? null : readPcs(capAssignmentFile);
        this.catalog = catalogFile == null ? null : readCatalog(catalogFile);
        this.serviceCatalog = serviceCatalogFile == null ? null : readServiceCatalog(serviceCatalogFile);
        this.tardocCatalog = tardocCatalogFile == null ? null : readTardocCatalog(tardocCatalogFile);
        this.mapper = (serviceCatalog == null || tardocCatalog == null) ? null : createMapper(serviceCatalog, tardocCatalog);
    }

    public String healthJson() throws Exception {
        return "{"
                + "\"loaded\":true,"
                + "\"grouper_system\":" + pathJson(grouperSystemFile) + ","
                + "\"cap_assignment_system\":" + pathJson(capAssignmentFile) + ","
                + "\"catalog\":" + pathJson(catalogFile) + ","
                + "\"service_catalog\":" + pathJson(serviceCatalogFile) + ","
                + "\"tardoc_catalog\":" + pathJson(tardocCatalogFile) + ","
                + "\"mapper_loaded\":" + (mapper != null) + ","
                + "\"pcs\":{" 
                + "\"name\":" + quote(str(invoke(grouperPcs, "getName"))) + ","
                + "\"version\":" + quote(str(invoke(grouperPcs, "getVersion"))) + ","
                + "\"data_year\":" + quote(str(invoke(grouperPcs, "getDataYear"))) + ","
                + "\"application_year\":" + quote(str(invoke(grouperPcs, "getApplicationYear")))
                + "}"
                + "}";
    }

    public String evaluateGrouper(String requestBody) throws Exception {
        Map<?, ?> root = parseJsonObject(requestBody);
        Object patientNode = root.containsKey("patient_case") ? root.get("patient_case") : root;
        if (!(patientNode instanceof Map<?, ?> patient)) {
            throw new IllegalArgumentException("patient_case must be a JSON object");
        }
        Object pc = buildPatientCase(patient);

        String requestedCapitulum = stringValue(patient.get("capitulum"));
        if (requestedCapitulum != null && !requestedCapitulum.isBlank()) {
            invoke(pc, "setCapitulum", new Class<?>[]{String.class}, requestedCapitulum);
        } else if (capAssignmentPcs != null) {
            Object capResult = invoke(capAssignmentPcs, "evaluate", new Class<?>[]{cls("ch.oaat_otma.PatientCase")}, pc);
            String cap = stringValue(field(capResult, "group"));
            if (cap != null && !cap.isBlank()) {
                invoke(pc, "setCapitulum", new Class<?>[]{String.class}, cap);
            }
        }

        addServices(pc, patient);
        addDrugs(pc, patient);
        Object result = invoke(grouperPcs, "evaluate", new Class<?>[]{cls("ch.oaat_otma.PatientCase")}, pc);
        return resultJson(result, pc);
    }

    public String evaluateMapper(String requestBody) throws Exception {
        if (mapper == null) {
            throw new IllegalStateException("Mapper runtime files are missing. Expected lkaat_*.json and tardoc_*_de.json in " + config.dataDir());
        }
        Map<?, ?> root = parseJsonObject(requestBody);
        Object patientNode = root.containsKey("patient_case") ? root.get("patient_case") : root;
        if (!(patientNode instanceof Map<?, ?> patient)) {
            throw new IllegalArgumentException("patient_case must be a JSON object");
        }
        Object pc = buildPatientCase(patient);
        addServices(pc, patient);
        addDrugs(pc, patient);
        Object result = invoke(mapper, "mapByValue", new Class<?>[]{cls("ch.oaat_otma.PatientCase")}, pc);
        return mapperResultJson(result);
    }

    private Object buildPatientCase(Map<?, ?> patient) throws Exception {
        Object pc = cls("ch.oaat_otma.PatientCase").getConstructor().newInstance();
        String sex = stringValue(patient.get("sex"));
        if (sex != null) invoke(pc, "setSex", new Class<?>[]{String.class}, sex);
        Integer ageYears = intValue(patient.get("age_years"));
        if (ageYears != null) invoke(pc, "setAgeYears", new Class<?>[]{Integer.class}, ageYears);
        Integer ageDays = intValue(patient.get("age_days"));
        if (ageDays != null) invoke(pc, "setAgeDays", new Class<?>[]{Integer.class}, ageDays);
        String entryDate = stringValue(patient.get("entry_date"));
        if (entryDate != null && !entryDate.isBlank()) {
            invoke(pc, "setEntryDate", new Class<?>[]{LocalDate.class}, LocalDate.parse(entryDate));
        }
        String birthDate = stringValue(patient.get("birth_date"));
        if (birthDate != null && !birthDate.isBlank()) {
            invoke(pc, "setBirthDate", new Class<?>[]{LocalDate.class}, LocalDate.parse(birthDate));
        }
        String diagnosis = stringValue(patient.get("diagnosis"));
        if (diagnosis == null || diagnosis.isBlank()) throw new IllegalArgumentException("diagnosis is required");
        Object diag = cls("ch.oaat_otma.Diagnosis").getConstructor(String.class).newInstance(diagnosis);
        invoke(pc, "setDiagnosis", new Class<?>[]{cls("ch.oaat_otma.Diagnosis")}, diag);
        return pc;
    }

    private void addServices(Object pc, Map<?, ?> patient) throws Exception {
        Object raw = patient.get("services");
        if (!(raw instanceof List<?> services) || services.isEmpty()) {
            throw new IllegalArgumentException("services must be a non-empty JSON array");
        }
        Class<?> sideClass = cls("ch.oaat_otma.Side");
        Class<?> serviceClass = cls("ch.oaat_otma.Service");
        Constructor<?> serviceCtor = serviceClass.getConstructor(String.class, sideClass, int.class, LocalDate.class, Integer.class);
        LocalDate fallbackDate = LocalDate.now();
        String entryDate = stringValue(patient.get("entry_date"));
        if (entryDate != null && !entryDate.isBlank()) fallbackDate = LocalDate.parse(entryDate);

        for (Object item : services) {
            if (!(item instanceof Map<?, ?> serviceMap)) throw new IllegalArgumentException("Each service must be an object");
            String code = normalizeServiceCode(stringValue(serviceMap.get("code")));
            if (code == null || code.isBlank()) throw new IllegalArgumentException("Each service must include code");
            Integer number = intValue(serviceMap.get("quantity"));
            if (number == null) number = intValue(serviceMap.get("number"));
            if (number == null) number = 1;
            String sideString = stringValue(serviceMap.get("side"));
            if (sideString == null || sideString.isBlank()) sideString = "NONE";
            Object side = sideClass.getMethod("valueOf", String.class).invoke(null, sideString.toUpperCase());
            String dateString = stringValue(serviceMap.get("date"));
            LocalDate date = (dateString == null || dateString.isBlank()) ? fallbackDate : LocalDate.parse(dateString);
            Integer session = intValue(serviceMap.get("session"));
            if (session == null) session = intValue(serviceMap.get("session_number"));
            if (session == null) session = 1;
            Object service = serviceCtor.newInstance(code, side, number, date, session);
            invoke(pc, "addService", new Class<?>[]{serviceClass}, service);
        }
    }

    private void addDrugs(Object pc, Map<?, ?> patient) throws Exception {
        Object raw = patient.get("drugs");
        if (raw == null) return;
        if (!(raw instanceof List<?> drugs)) {
            throw new IllegalArgumentException("drugs must be a JSON array when provided");
        }
        Class<?> drugClass = cls("ch.oaat_otma.Drug");
        Constructor<?> drugCtor = drugClass.getConstructor(String.class, String.class, String.class, Number.class, String.class, LocalDate.class, Integer.class);
        LocalDate fallbackDate = LocalDate.now();
        String entryDate = stringValue(patient.get("entry_date"));
        if (entryDate != null && !entryDate.isBlank()) fallbackDate = LocalDate.parse(entryDate);

        for (Object item : drugs) {
            if (!(item instanceof Map<?, ?> drugMap)) throw new IllegalArgumentException("Each drug must be an object");
            String code = stringValue(firstPresent(drugMap, "code", "atc"));
            if (code == null || code.isBlank()) throw new IllegalArgumentException("Each drug must include code/atc");
            String annex = stringValueOrDefault(drugMap.get("annex"), "");
            String application = stringValueOrDefault(drugMap.get("application"), "");
            Number dose = numberValue(firstPresent(drugMap, "dose", "quantity", "amount"));
            if (dose == null) throw new IllegalArgumentException("Each drug must include dose/quantity/amount");
            String unit = stringValueOrDefault(drugMap.get("unit"), "");
            String dateString = stringValue(drugMap.get("date"));
            LocalDate date = (dateString == null || dateString.isBlank()) ? fallbackDate : LocalDate.parse(dateString);
            Integer session = intValue(drugMap.get("session"));
            if (session == null) session = intValue(drugMap.get("session_number"));
            if (session == null) session = 1;
            Object drug = drugCtor.newInstance(code, annex == null ? "" : annex, application == null ? "" : application, dose, unit == null ? "" : unit, date, session);
            invoke(pc, "addDrug", new Class<?>[]{drugClass}, drug);
        }
    }

    private String resultJson(Object result, Object pc) throws Exception {
        String group = stringValue(field(result, "group"));
        Object groups = field(result, "groups");
        Object decisionPath = field(result, "decisionPath");
        Object errors = field(result, "errors");
        boolean reimbursedByFlatrates = (boolean) invoke(result, "isReimbursedByFlatrates");
        Integer taxPoints = null;
        if (catalog != null && group != null) {
            Object tax = invoke(catalog, "getTaxPoints", new Class<?>[]{String.class}, group);
            if (tax instanceof Integer i) taxPoints = i;
        }
        return "{"
                + "\"ok\":" + (collectionSize(errors) == 0) + ","
                + "\"group\":" + quote(group) + ","
                + "\"groups\":" + collectionJson(groups) + ","
                + "\"capitulum\":" + quote(stringValue(invoke(pc, "getCapitulum"))) + ","
                + "\"reimbursed_by_flatrates\":" + reimbursedByFlatrates + ","
                + "\"tax_points\":" + (taxPoints == null ? "null" : taxPoints.toString()) + ","
                + "\"errors\":" + errorsJson(errors) + ","
                + "\"decision_path\":" + decisionsJson(decisionPath) + ","
                + "\"services\":" + servicesJson(invoke(pc, "getServices")) + ","
                + "\"drugs\":" + drugsJson(invoke(pc, "getDrugs"))
                + "}";
    }

    private String mapperResultJson(Object result) throws Exception {
        Object resultPc = field(result, "patientCase");
        Object addedTarpos = field(result, "addedTarpos");
        Object log = field(result, "log");
        return "{"
                + "\"ok\":" + !hasProblemMapperLog(log) + ","
                + "\"added_tarpos\":" + tarposJson(addedTarpos) + ","
                + "\"tarpos\":" + tarposJson(invoke(resultPc, "getTarpos")) + ","
                + "\"log\":" + mapperLogJson(log) + ","
                + "\"services\":" + servicesJson(invoke(resultPc, "getServices"))
                + "}";
    }

    private boolean hasProblemMapperLog(Object log) throws Exception {
        if (!(log instanceof Collection<?> col)) return false;
        for (Object entry : col) {
            String level = str(field(entry, "level"));
            if (level != null && (level.contains("ERROR") || level.contains("DELETE"))) {
                return true;
            }
        }
        return false;
    }

    private Object logEntriesByLevel(Object log, String level) throws Exception {
        List<Object> entries = new ArrayList<>();
        if (log instanceof Collection<?> col) {
            for (Object entry : col) {
                if (level.equals(str(field(entry, "level")))) entries.add(entry);
            }
        }
        return entries;
    }

    private String tarposJson(Object tarpos) throws Exception {
        if (!(tarpos instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object tarpo : col) {
            out.add("{\"code\":" + quote(str(field(tarpo, "code")))
                    + ",\"tariff\":" + quote(str(field(tarpo, "tariff")))
                    + ",\"number\":" + field(tarpo, "number")
                    + ",\"amount\":" + field(tarpo, "amount")
                    + ",\"session_number\":" + field(tarpo, "sessionNumber")
                    + ",\"side\":" + quote(str(field(tarpo, "side")))
                    + ",\"date\":" + quote(str(field(tarpo, "date"))) + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private String mapperLogJson(Object log) throws Exception {
        if (!(log instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object entry : col) {
            out.add("{\"level\":" + quote(str(field(entry, "level")))
                    + ",\"message\":" + quote(str(field(entry, "message")))
                    + ",\"service_code\":" + quote(str(field(entry, "serviceCode")))
                    + ",\"tardoc_code\":" + quote(str(field(entry, "tardocCode")))
                    + ",\"session_number\":" + field(entry, "sessionNumber")
                    + ",\"side\":" + quote(str(field(entry, "side")))
                    + ",\"date\":" + quote(str(field(entry, "date"))) + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private String errorsJson(Object errors) throws Exception {
        if (!(errors instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object error : col) {
            out.add("{\"type\":" + quote(str(field(error, "type"))) + ",\"message\":" + quote(str(field(error, "message"))) + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private String decisionsJson(Object decisions) throws Exception {
        if (!(decisions instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object decision : col) {
            out.add("{\"node_id\":" + quote(str(field(decision, "nodeId")))
                    + ",\"node_name\":" + quote(str(field(decision, "nodeName")))
                    + ",\"explanation\":" + quote(str(field(decision, "explanation"))) + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private String servicesJson(Object services) throws Exception {
        if (!(services instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object service : col) {
            out.add("{\"code\":" + quote(str(field(service, "code")))
                    + ",\"used\":" + invoke(service, "isUsed")
                    + ",\"side\":" + quote(str(field(service, "side")))
                    + ",\"number\":" + field(service, "number") + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private String drugsJson(Object drugs) throws Exception {
        if (!(drugs instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object drug : col) {
            out.add("{\"code\":" + quote(str(field(drug, "code")))
                    + ",\"annex\":" + quote(str(field(drug, "annex")))
                    + ",\"application\":" + quote(str(field(drug, "application")))
                    + ",\"dose\":" + field(drug, "dose")
                    + ",\"unit\":" + quote(str(field(drug, "unit")))
                    + ",\"session_number\":" + field(drug, "sessionNumber")
                    + ",\"date\":" + quote(str(field(drug, "date"))) + "}");
        }
        return "[" + String.join(",", out) + "]";
    }

    private Object readPcs(Path path) throws Exception {
        if (path == null) throw new IllegalStateException("Missing grouper system file in " + config.dataDir());
        Object reader = cls("ch.oaat_otma.grouper.ClassificationSystemReader").getConstructor().newInstance();
        return reader.getClass().getMethod("readFromFile", File.class).invoke(reader, path.toFile());
    }

    private Object readCatalog(Path path) throws Exception {
        Class<?> catalogClass = cls("ch.oaat_otma.grouper.Catalog");
        return catalogClass.getMethod("readFromFile", File.class).invoke(null, path.toFile());
    }

    private Object readServiceCatalog(Path path) throws Exception {
        Class<?> catalogClass = cls("ch.oaat_otma.mapper.ServiceCatalog");
        return catalogClass.getMethod("readCatalog", File.class).invoke(null, path.toFile());
    }

    private Object readTardocCatalog(Path path) throws Exception {
        Class<?> catalogClass = cls("ch.oaat_otma.mapper.TardocCatalog");
        return catalogClass.getMethod("readCatalog", File.class).invoke(null, path.toFile());
    }

    private Object createMapper(Object serviceCatalog, Object tardocCatalog) throws Exception {
        Class<?> serviceCatalogClass = cls("ch.oaat_otma.mapper.ServiceCatalog");
        Class<?> tardocCatalogClass = cls("ch.oaat_otma.mapper.TardocCatalog");
        return cls("ch.oaat_otma.mapper.Mapper").getConstructor(serviceCatalogClass, tardocCatalogClass).newInstance(serviceCatalog, tardocCatalog);
    }

    private Map<?, ?> parseJsonObject(String body) throws Exception {
        Object parsed = gson.getClass().getMethod("fromJson", String.class, Class.class).invoke(gson, body, Map.class);
        if (!(parsed instanceof Map<?, ?> map)) throw new IllegalArgumentException("JSON body must be an object");
        return map;
    }

    private Path firstFile(String glob) throws Exception {
        try (var stream = Files.newDirectoryStream(config.dataDir(), glob)) {
            for (Path path : stream) return path;
        }
        return null;
    }

    private Class<?> cls(String name) throws ClassNotFoundException { return Class.forName(name, true, loader); }

    private Object invoke(Object target, String method) throws Exception {
        return target.getClass().getMethod(method).invoke(target);
    }

    private Object invoke(Object target, String method, Class<?>[] types, Object... args) throws Exception {
        return target.getClass().getMethod(method, types).invoke(target, args);
    }

    private Object field(Object target, String field) throws Exception {
        Field f = target.getClass().getField(field);
        return f.get(target);
    }

    private static String normalizeServiceCode(String code) {
        if (code == null) return null;
        String value = code.trim();
        if (value.matches("^[0-9]+x[A-Z].*")) return value.replaceFirst("^[0-9]+x", "");
        return value;
    }

    private static Object firstPresent(Map<?, ?> map, String... keys) {
        for (String key : keys) {
            if (map.containsKey(key)) return map.get(key);
        }
        return null;
    }

    private static Number numberValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number;
        String text = value.toString();
        if (text.contains(".")) return Double.parseDouble(text);
        return Integer.parseInt(text);
    }

    private static Integer intValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.intValue();
        return Integer.parseInt(value.toString());
    }

    private static String stringValue(Object value) { return value == null ? null : value.toString(); }
    private static String stringValueOrDefault(Object value, String fallback) { return value == null ? fallback : value.toString(); }
    private static String str(Object value) { return value == null ? null : value.toString(); }
    private static int collectionSize(Object value) { return value instanceof Collection<?> c ? c.size() : 0; }

    private static String collectionJson(Object value) {
        if (!(value instanceof Collection<?> col)) return "[]";
        List<String> out = new ArrayList<>();
        for (Object item : col) out.add(quote(str(item)));
        return "[" + String.join(",", out) + "]";
    }

    private static String pathJson(Path path) {
        if (path == null) return "null";
        return "{\"path\":" + quote(path.toString()) + ",\"present\":" + Files.exists(path) + "}";
    }

    private static String quote(String value) {
        if (value == null) return "null";
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }
}
