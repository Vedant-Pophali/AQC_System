package qc.pipeline;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.exec.CommandLine;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.awt.Desktop;
import java.io.File;
import java.nio.file.Paths;
import java.util.function.Consumer;

public class WorkflowManager {
    private static final Logger logger = LoggerFactory.getLogger(WorkflowManager.class);
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final JobExecutor jobExecutor = new JobExecutor();

    // CONFIGURATION
    private static final String CONTAINER_NAME = "qc_worker_1";
    private static final String DOCKER_INPUT_PATH = "/app/temp_upload/test_video.mp4";
    private static final String DOCKER_JSON_PATH = "/app/reports/Master_Report.json";
    private static final String DOCKER_HTML_PATH = "/app/reports/dashboard.html";
    private static final String LOCAL_PROJECT_ROOT = System.getProperty("user.dir");
    private static final String LOCAL_OUTPUT_DIR = Paths.get(LOCAL_PROJECT_ROOT, "reports").toString();

    /**
     * Now accepts a 'uiLogger' to send messages back to the GUI
     */
    public void runQualityControlPipeline(String localVideoName, Consumer<String> uiLogger) {
        File videoFile = new File(localVideoName);
        if (!videoFile.exists()) {
            uiLogger.accept("[ERROR] Video not found: " + localVideoName);
            return;
        }

        uiLogger.accept("==========================================");
        uiLogger.accept(" QC ORCHESTRATOR STARTED");
        uiLogger.accept(" Target: " + videoFile.getName());
        uiLogger.accept("==========================================");

        new File(LOCAL_OUTPUT_DIR).mkdirs();

        // 1. UPLOAD
        uiLogger.accept("[Step 1/3] Uploading video to Secure Container...");
        executeDockerCommand("cp", videoFile.getAbsolutePath(), CONTAINER_NAME + ":" + DOCKER_INPUT_PATH);
        uiLogger.accept("   > Upload Complete.");

        // 2. ANALYZE
        uiLogger.accept("[Step 2/3] Triggering Distributed Spark Engine...");
        uiLogger.accept("   > This may take 30-60 seconds depending on video length.");
        uiLogger.accept("   > Please wait...");

        CommandLine sparkCmd = new CommandLine("docker");
        sparkCmd.addArgument("exec");
        sparkCmd.addArgument(CONTAINER_NAME);
        sparkCmd.addArgument("spark-submit");
        sparkCmd.addArgument("src/main.py");
        sparkCmd.addArgument("--input");
        sparkCmd.addArgument(DOCKER_INPUT_PATH);
        sparkCmd.addArgument("--output");
        sparkCmd.addArgument("/app/reports");

        JobExecutor.ExecutionResult result = jobExecutor.executeCommand(sparkCmd);

        if (result.exitCode == 0) {
            uiLogger.accept("   > Engine Analysis Finished.");

            // 3. DOWNLOAD
            uiLogger.accept("[Step 3/3] Downloading Intelligence Reports...");
            String localJsonPath = Paths.get(LOCAL_OUTPUT_DIR, "Master_Report.json").toString();
            String localHtmlPath = Paths.get(LOCAL_OUTPUT_DIR, "dashboard.html").toString();

            executeDockerCommand("cp", CONTAINER_NAME + ":" + DOCKER_JSON_PATH, localJsonPath);
            executeDockerCommand("cp", CONTAINER_NAME + ":" + DOCKER_HTML_PATH, localHtmlPath);

            uiLogger.accept("   > Reports Saved to: " + LOCAL_OUTPUT_DIR);

            // 4. PARSE & DISPLAY
            try {
                JsonNode root = objectMapper.readTree(new File(localJsonPath));
                String status = root.path("overall_status").asText("UNKNOWN");
                uiLogger.accept("------------------------------------------");
                uiLogger.accept(" FINAL VERDICT: " + status);
                uiLogger.accept("------------------------------------------");
            } catch (Exception e) {
                uiLogger.accept("[WARN] Could not parse summary text.");
            }

            openDashboard(localHtmlPath, uiLogger);

        } else {
            uiLogger.accept("[FAILURE] Spark Engine Crashed.");
            uiLogger.accept("STDERR: " + result.errorLogs);
        }
    }

    private void executeDockerCommand(String... args) {
        CommandLine cmd = new CommandLine("docker");
        for (String arg : args) cmd.addArgument(arg);
        JobExecutor.ExecutionResult res = jobExecutor.executeCommand(cmd);
        if (res.exitCode != 0) {
            throw new RuntimeException("Docker failure: " + res.errorLogs);
        }
    }

    private void openDashboard(String htmlPath, Consumer<String> uiLogger) {
        try {
            File htmlFile = new File(htmlPath);
            if (htmlFile.exists() && Desktop.isDesktopSupported()) {
                uiLogger.accept("[INFO] Launching Browser Dashboard...");
                Desktop.getDesktop().browse(htmlFile.toURI());
            }
        } catch (Exception e) {
            uiLogger.accept("[WARN] Browser auto-launch failed.");
        }
    }
}