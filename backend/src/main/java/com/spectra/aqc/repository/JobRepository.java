package com.spectra.aqc.repository;

import com.spectra.aqc.model.QualityControlJob;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface JobRepository extends JpaRepository<QualityControlJob, Long> {
}
