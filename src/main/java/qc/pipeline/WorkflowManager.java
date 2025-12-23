package qc.pipeline;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.exec.CommandLine;
import org.apache.commons.exec.DefaultExecutor;
import org.apache.commons.exec.PumpStreamHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.nio.file.Paths;

public class WorkflowManager {
    private static final Logger logger = LoggerFactory.getLogger(WorkflowManager.class);
    private final ObjectMapper objectMapper = new ObjectMapper();

    // 1. DYNAMICALLY RESOLVE PATHS (No hardcoding)
    private static final String PROJECT_ROOT = System.getProperty("user.dir");

    // Use the venv Python to ensure libraries (CV2, EasyOCR) are found
    private static final String PYTHON_EXEC = Paths.get(PROJECT_ROOT, "venv", "Scripts", "python.exe").toString();

    // The main entry point script
    private static final String MAIN_SCRIPT = Paths.get(PROJECT_ROOT, "src", "main.py").toString();

    // Where reports will land
    private static final String OUTPUT_DIR = Paths.get(PROJECT_ROOT, "reports").toString();

    public void runQualityControlPipeline(String videoFileName) {
        String videoPath = Paths.get(videoFileName).toAbsolutePath().toString();

        logger.info("==========================================");
        logger.info(" STARTING QC PIPELINE");
        logger.info(" Python Engine: {}", PYTHON_EXEC);
        logger.info(" Target Video:  {}", videoPath);
        logger.info("==========================================");

        // 2. CONSTRUCT THE COMMAND
        // We call main.py, which handles all sub-modules (Visual, Audio, OCR, Dashboard)
        CommandLine cmdLine = new CommandLine(PYTHON_EXEC);
        cmdLine.addArgument(MAIN_SCRIPT);
        cmdLine.addArgument("--input");
        cmdLine.addArgument(videoPath, true); // true = handle quoting for spaces
        cmdLine.addArgument("--output");
        cmdLine.addArgument(OUTPUT_DIR, true);

        // 3. EXECUTE
        int exitCode = executeCommand(cmdLine);

        // 4. PROCESS RESULTS
        if (exitCode == 0) {
            String masterReportPath = Paths.get(OUTPUT_DIR, "Master_Report.json").toString();
            String dashboardPath = Paths.get(OUTPUT_DIR, "dashboard.html").toString();

            logger.info("[SUCCESS] Pipeline finished. Parsing results...");
            parseAndPrintResult(masterReportPath);

            // Auto-open dashboard
            try {
                logger.info("Opening Dashboard: {}", dashboardPath);
                Runtime.getRuntime().exec("cmd /c start " + dashboardPath);
            } catch (Exception e) {
                logger.warn("Could not auto-open browser: " + e.getMessage());
            }
        } else {
            logger.error("[FAILURE] Pipeline exited with code {}", exitCode);
        }
    }

    private int executeCommand(CommandLine cmdLine) {
        DefaultExecutor executor = new DefaultExecutor();

        // Capture output to log it in real-time or debug
        ByteArrayOutputStream outStream = new ByteArrayOutputStream();
        ByteArrayOutputStream errStream = new ByteArrayOutputStream();
        PumpStreamHandler streamHandler = new PumpStreamHandler(outStream, errStream);
        executor.setStreamHandler(streamHandler);

        // Allow non-zero exit codes to be handled manually
        executor.setExitValues(null);

        try {
            int exitValue = executor.execute(cmdLine);

            // Print Python logs to Java Logger
            logger.info("--- PYTHON LOGS ---");
            logger.info(outStream.toString());

            if (exitValue != 0) {
                logger.error("--- PYTHON ERRORS ---");
                logger.error(errStream.toString());
            }

            return exitValue;
        } catch (IOException e) {
            logger.error("Execution failed", e);
            return -1;
        }
    }

    private void parseAndPrintResult(String jsonPath) {
        try {
            File reportFile = new File(jsonPath);
            if (!reportFile.exists()) {
                logger.error("Report file not found: {}", jsonPath);
                return;
            }

            JsonNode rootNode = objectMapper.readTree(reportFile);
            String status = rootNode.path("overall_status").asText("UNKNOWN");

            logger.info("------------------------------------------");
            logger.info(" FINAL REPORT SUMMARY");
            logger.info(" Overall Status: {}", status);

            JsonNode modules = rootNode.path("modules");
            if (modules.isObject()) {
                modules.fieldNames().forEachRemaining(moduleName -> {
                    String modStatus = modules.get(moduleName).path("status").asText();
                    int eventCount = modules.get(moduleName).path("events").size();
                    logger.info(" > {}: {} ({} events)", moduleName, modStatus, eventCount);
                });
            }
            logger.info("------------------------------------------");

        } catch (Exception e) {
            logger.error("Failed to parse Master JSON", e);
        }
    }

    public static void main(String[] args) {
        // Point to a test video file in your project root
        new WorkflowManager().runQualityControlPipeline("video.mp4");
    }
}