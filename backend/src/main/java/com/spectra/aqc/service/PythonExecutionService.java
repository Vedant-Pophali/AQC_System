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

    @Value("${app.aqc.spark.segment-duration:60}")
    private String sparkSegmentDuration;

    @Value("${app.aqc.execution-mode:LOCAL}")
    private String executionMode;

    @org.springframework.beans.factory.annotation.Autowired
    private com.spectra.aqc.repository.JobRepository jobRepository;

    private File resolveMainScript() {
        // 1. Try configured path
        File f = new File(scriptPath);
        if (f.exists()) {
             logger.info("Found script at configured path: " + f.getAbsolutePath());
             return f.getAbsoluteFile();
        }
        
        // 2. Try relative to current dir (e.g. if CWD is /app)
        f = new File("main.py");
        if (f.exists()) {
             logger.info("Found script at current dir: " + f.getAbsolutePath());
             return f.getAbsoluteFile();
        }

        // 3. Try parent dir (e.g. if CWD is /app/backend)
        f = new File("../main.py");
        if (f.exists()) {
             logger.info("Found script at parent dir: " + f.getAbsolutePath());
             return f.getAbsoluteFile();
        }
        
        // NEW: Try backend-bundled path (python_core/main.py)
        f = new File("python_core/main.py");
        if (f.exists()) {
             logger.info("Found script at bundled path: " + f.getAbsolutePath());
             return f.getAbsoluteFile();
        }

        // 4. Try standard Render/Docker path
        f = new File("/app/python_core/main.py");
        if (f.exists()) {
             logger.info("Found script at /app/python_core/main.py: " + f.getAbsolutePath());
             return f.getAbsoluteFile();
        }
        
        // Fallback to configured path
        logger.warn("Script detection failed. Defaulting to: " + scriptPath);
        return new File(scriptPath).getAbsoluteFile();
    }

    public CompletableFuture<String> runAnalysis(Long jobId, String inputFilePath, String profile) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                // ... (existing REMOTE check logic) ...
                if ("REMOTE".equalsIgnoreCase(executionMode)) {
                     throw new JobQueuedException("Job " + jobId + " queued for remote execution.");
                }

                File scriptFile = resolveMainScript();
                File sparkScriptFile = new File(sparkScriptPath).getCanonicalFile();

                File targetScript;
                boolean isSpark = "SPARK".equalsIgnoreCase(engineType);
                
                if (isSpark) {
                    // Try to resolve spark script similar to main script
                    File sparkF = new File(sparkScriptPath);
                    if (!sparkF.exists()) {
                         // Try bundled path
                         sparkF = new File("python_core/main_spark.py");
                    }
                     if (!sparkF.exists()) {
                         // Try Render path
                         sparkF = new File("/app/python_core/main_spark.py");
                    }
                    
                    if (!sparkF.exists()) {
                         throw new RuntimeException("Spark engine requested but script not found at: " + sparkScriptPath + " or bundled paths");
                    }
                    targetScript = sparkF.getAbsoluteFile();
                } else {
                    // Monolith (Main)
                    File scriptFile = resolveMainScript();
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
                    command.add("--segments");
                    command.add(sparkSegmentDuration);
                } else {
                    command.add("--hwaccel");
                    command.add(hwaccelEnabled ? hwaccelDevice : "none");
                }

                ProcessBuilder pb = new ProcessBuilder(command);
                pb.directory(scriptFile.getParentFile());
                pb.redirectErrorStream(true);
                Process process = pb.start();

                // Regex for parsing progress: [PROGRESS] 25 - Checking Video Frames
                java.util.regex.Pattern progressPattern = java.util.regex.Pattern.compile("\\[PROGRESS\\]\\s+(\\d+)(?:\\s+-\\s+(.*))?");

                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        System.out.println("[Job " + jobId + " Python]: " + line);
                        
                        // Parse Progress
                        java.util.regex.Matcher matcher = progressPattern.matcher(line);
                        if (matcher.find()) {
                            try {
                                int progress = Integer.parseInt(matcher.group(1));
                                String step = matcher.group(2);
                                
                                com.spectra.aqc.model.QualityControlJob job = jobRepository.findById(jobId).orElse(null);
                                if (job != null) {
                                    job.setProgress(progress);
                                    if (step != null && !step.isEmpty()) {
                                        job.setCurrentStep(step);
                                    }
                                    jobRepository.save(job);
                                }
                            } catch (Exception e) {
                                logger.error("Error updating progress for job " + jobId, e);
                            }
                        }
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

            } catch (JobQueuedException e) {
                 throw e; 
            } catch (Exception e) {
                throw new RuntimeException("Analysis failed: " + e.getMessage(), e);
            }
        });
    }

    public static class JobQueuedException extends RuntimeException {
        public JobQueuedException(String message) { super(message); }
    }
    public CompletableFuture<String> runRemediation(Long jobId, String inputFilePath, String fixType) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                // Resolve fix_media.py relative to main.py
                // Use dynamic resolution to handle Render environment (/app vs local)
                File mainScript = resolveMainScript();
                Path remediationScriptPath = mainScript.getParentFile().toPath()
                    .resolve("src").resolve("remediation").resolve("fix_media.py");
                
                File fixScript = remediationScriptPath.toFile();
                if (!fixScript.exists()) {
                logger.error("Remediation script NOT found: " + fixScript.getAbsolutePath());
                // Debugging: List files in the parent directory to see what's there
                File parentDir = mainScript.getParentFile();
                if (parentDir != null && parentDir.exists()) {
                     File srcDir = new File(parentDir, "src");
                     logger.error("Checking src dir: " + srcDir.getAbsolutePath());
                     if (srcDir.exists()) {
                         File remDir = new File(srcDir, "remediation");
                         logger.error("Checking remediation dir: " + remDir.getAbsolutePath());
                         if (remDir.exists()) {
                             String[] files = remDir.list();
                             logger.error("Files in remediation: " + (files != null ? java.util.Arrays.toString(files) : "null"));
                         } else {
                             logger.error("Remediation dir does NOT exist.");
                             String[] srcFiles = srcDir.list();
                             logger.error("Files in src: " + (srcFiles != null ? java.util.Arrays.toString(srcFiles) : "null"));
                         }
                     } else {
                         logger.error("Src dir does NOT exist at: " + srcDir.getAbsolutePath());
                         String[] parentFiles = parentDir.list();
                         logger.error("Files in parent: " + (parentFiles != null ? java.util.Arrays.toString(parentFiles) : "null"));
                     }
                }
                throw new RuntimeException("Remediation failed: Remediation script not found at: " + fixScript.getAbsolutePath());
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
