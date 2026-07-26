package com.loan4u.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.loan4u.data.PredictionDao
import com.loan4u.data.PredictionEntity
import com.loan4u.features.FeatureEngineering
import com.loan4u.features.HouseType
import com.loan4u.features.PropertyInput
import com.loan4u.services.MLModelService
import com.loan4u.services.PredictionResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import java.security.MessageDigest
import javax.inject.Inject

@HiltViewModel
class PropertyInputViewModel @Inject constructor(
    private val modelService: MLModelService,
    private val predictionDao: PredictionDao,
) : ViewModel() {
    private val _property = MutableStateFlow(PropertyInput())
    val property: StateFlow<PropertyInput> = _property

    private val _selectedRegion = MutableStateFlow<String?>(null)
    val selectedRegion: StateFlow<String?> = _selectedRegion

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _predictionResult = MutableStateFlow<PredictionResult?>(null)
    val predictionResult: StateFlow<PredictionResult?> = _predictionResult

    fun updateProperty(property: PropertyInput) {
        _property.value = property
    }

    fun setRegion(region: String?) {
        _selectedRegion.value = region
    }

    fun predict() {
        _isLoading.value = true
        viewModelScope.launch {
            try {
                val features = FeatureEngineering.buildFeatures(_property.value)
                val hash = hashFeatures(features)

                val cached = predictionDao.getPredictionByHash(hash)
                if (cached != null) {
                    _predictionResult.value = PredictionResult(
                        predictedPrice = cached.predictedPrice,
                        confidenceScore = cached.confidenceScore,
                        region = cached.region,
                        timestamp = cached.timestamp,
                    )
                    _isLoading.value = false
                    return@launch
                }

                val result = modelService.predict(features, _selectedRegion.value)
                if (result != null) {
                    _predictionResult.value = result
                    predictionDao.insertPrediction(
                        PredictionEntity(
                            predictedPrice = result.predictedPrice,
                            confidenceScore = result.confidenceScore,
                            region = result.region,
                            timestamp = result.timestamp,
                            featuresHash = hash,
                        )
                    )

                    val ttlMs = 86400000L
                    predictionDao.deletePredictionsBefore(System.currentTimeMillis() - ttlMs)
                }
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun resetForm() {
        _property.value = PropertyInput()
        _selectedRegion.value = null
        _predictionResult.value = null
    }

    private fun hashFeatures(features: Map<String, Float>): String {
        val str = features.toSortedMap().entries.joinToString(",") { "${it.key}:${it.value}" }
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(str.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}
