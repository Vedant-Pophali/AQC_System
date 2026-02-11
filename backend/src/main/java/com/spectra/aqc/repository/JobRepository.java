package com.spectra.aqc.repository;

import com.spectra.aqc.model.QualityControlJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface JobRepository extends JpaRepository<QualityControlJob, Long> {
    List<QualityControlJob> findAllByOrderByCreatedAtDesc();
    
    List<QualityControlJob> findByStatus(QualityControlJob.JobStatus status);
    
    List<QualityControlJob> findByFixStatus(String fixStatus);
}
