package com.spectra.aqc.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.CompletableFuture;

@Service
public class PythonExecutionService {

    private static final Logger logger = org.slf4j.LoggerFactory.getLogger(PythonExecutionService.class);

    @Value("${app.aqc.script-path:../main.py}")
    private String scriptPath;

    @Value("${app.aqc.spark-script-path:../main_spark.py}")
    private String sparkScriptPath;

    @Value("${app.aqc.engine:MONOLITH}")
    private String engineType;
    
    @Value("${app.storage.upload-dir}")
    private String outputDir;

    @Value("${app.aqc.hwaccel.enabled:false}")
    private boolean hwaccelEnabled;

    @Value("${app.aqc.hwaccel.device:cuda}")
    private String hwaccelDevice;

    @Value("${app.aqc.spark.master:local[*]}")
    private String sparkMaster;

    @Value("${app.aqc.spark.driver-memory:2g}")
    private String sparkDriverMemory;

    @Value("${app.aqc.spark.executor-memory:2g}")
    private String sparkExecutorMemory;

    @Value("${app.aqc.spark.cores:4}")
    private String sparkCores;

    public CompletableFuture<String> runAnalysis(Long jobId, String inputFilePath, String profile) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                File scriptFile = new File(scriptPath).getCanonicalFile();
                File sparkScriptFile = new File(sparkScriptPath).getCanonicalFile();

                File targetScript;
                boolean isSpark = "SPARK".equalsIgnoreCase(engineType);
                
                // Deterministic Logic based on Configuration
                if (isSpark) {
                    if (!sparkScriptFile.exists()) {
                         throw new RuntimeException("Spark engine requested but script not found at: " + sparkScriptFile.getAbsolutePath());
                    }
                    targetScript = sparkScriptFile;
                } else {
                    // Default to MONOLITH
                    if (!scriptFile.exists()) {
                        throw new RuntimeException("Monolith engine requested but script not found at: " + scriptFile.getAbsolutePath());
                    }
                    targetScript = scriptFile;
                }

                String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
                String resultDirName = "job_" + jobId + "_" + timestamp;
                Path resultDir = Paths.get(outputDir).resolve(resultDirName).toAbsolutePath();
                
                logger.info("Executing AQC analysis using Engine: " + engineType + " (Script: " + targetScript.getName() + ") with profile: " + profile);

                // Construct command
                java.util.List<String> command = new java.util.ArrayList<>();
                command.add("python");
                command.add(targetScript.getAbsolutePath());
                command.add("--input");
                command.add(inputFilePath);
                command.add("--outdir");
                command.add(resultDir.toString());
                command.add("--mode");
                command.add(profile);
                
                if (isSpark) {
                    command.add("--spark_master");
                    command.add(sparkMaster);
                    command.add("--spark_driver_memory");
                    command.add(sparkDriverMemory);
                    command.add("--spark_executor_memory");
                    command.add(sparkExecutorMemory);
                    command.add("--spark_cores");
                    command.add(sparkCores);
                } else {
                    // HW Accel is generally for Monolith/Local FFmpeg
                    command.add("--hwaccel");
                    command.add(hwaccelEnabled ? hwaccelDevice : "none");
                }

                ProcessBuilder pb = new ProcessBuilder(command);
                
                pb.directory(scriptFile.getParentFile());
                pb.redirectErrorStream(true);
                Process process = pb.start();

                // Capture output logic could go here (logging)
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        System.out.println("[Job " + jobId + " Python]: " + line);
                    }
                }

                int exitCode = process.waitFor();
                if (exitCode != 0) {
                    throw new RuntimeException("Python script exited with code " + exitCode);
                }

                // Find report file (it might be in a subdir named after the video)
                try (java.util.stream.Stream<Path> stream = java.nio.file.Files.walk(resultDir)) {
                    Path reportPath = stream
                        .filter(p -> p.getFileName().toString().equals("Master_Report.json"))
                        .findFirst()
                        .orElseThrow(() -> new RuntimeException("Master_Report.json not found in " + resultDir));
                    return reportPath.toAbsolutePath().toString();
                }

            } catch (Exception e) {
                throw new RuntimeException("Analysis failed: " + e.getMessage(), e);
            }
        });
    }
    public CompletableFuture<String> runRemediation(Long jobId, String inputFilePath, String fixType) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                // Resolve fix_media.py relative to main.py
                // scriptPath is usually path/to/main.py
                File mainScript = new File(scriptPath).getCanonicalFile();
                Path remediationScriptPath = mainScript.getParentFile().toPath()
                    .resolve("src").resolve("remediation").resolve("fix_media.py");
                
                File fixScript = remediationScriptPath.toFile();
                if (!fixScript.exists()) {
                     throw new RuntimeException("Remediation script not found at: " + fixScript.getAbsolutePath());
                }

                // Generate Output Path
                // e.g., input.mp4 -> input_fixed_loudness_norm.mp4
                File inputFile = new File(inputFilePath);
                String name = inputFile.getName();
                String baseName = name.contains(".") ? name.substring(0, name.lastIndexOf('.')) : name;
                String extension = name.contains(".") ? name.substring(name.lastIndexOf('.')) : ".mp4";
                
                String outputName = baseName + "_fixed_" + fixType + extension;
                Path output_path = inputFile.getParentFile().toPath().resolve(outputName);
                
                logger.info("Executing Remediation: " + fixType + " on Job " + jobId);

                java.util.List<String> command = new java.util.ArrayList<>();
                command.add("python");
                command.add(fixScript.getAbsolutePath());
                command.add("--input");
                command.add(inputFilePath);
                command.add("--output");
                command.add(output_path.toString());
                command.add("--fix");
                command.add(fixType);

                ProcessBuilder pb = new ProcessBuilder(command);
                pb.directory(fixScript.getParentFile());
                pb.redirectErrorStream(true);
                Process process = pb.start();

                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        System.out.println("[Job " + jobId + " Fix]: " + line);
                    }
                }

                int exitCode = process.waitFor();
                if (exitCode != 0) {
                    throw new RuntimeException("Remediation script exited with code " + exitCode);
                }

                // Return the fixed file path
                return output_path.toAbsolutePath().toString();

            } catch (Exception e) {
                throw new RuntimeException("Remediation failed: " + e.getMessage(), e);
            }
        });
    }
}
