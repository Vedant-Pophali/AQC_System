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

    public CompletableFuture<String> runAnalysis(Long jobId, String inputFilePath, String profile) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                File scriptFile = new File(scriptPath).getCanonicalFile();
                File sparkScriptFile = new File(sparkScriptPath).getCanonicalFile();

                File targetScript;
                
                // Deterministic Logic based on Configuration
                if ("SPARK".equalsIgnoreCase(engineType)) {
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

                // Construct command: python <script> --input <file> --outdir <dir> --mode <profile>
                ProcessBuilder pb = new ProcessBuilder(
                    "python",
                    targetScript.getAbsolutePath(),
                    "--input", inputFilePath,
                    "--outdir", resultDir.toString(),
                    "--mode", profile
                );
                
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
}
