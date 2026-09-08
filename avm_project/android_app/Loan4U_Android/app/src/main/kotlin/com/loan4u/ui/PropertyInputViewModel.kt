package com.loan4u.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.loan4u.data.PredictionDao
import com.loan4u.data.PredictionEntity
import com.loan4u.features.FeatureEngineering
import com.loan4u.features.PropertyInput
import com.loan4u.services.MLModelService
import com.loan4u.services.PredictionResult
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.security.MessageDigest
import javax.inject.Inject

@HiltViewModel
class PropertyInputViewModel @Inject constructor(
    private val modelService: MLModelService,
    private val predictionDao: PredictionDao,
) : ViewModel() {
    private val _property = MutableStateFlow(PropertyInput())
    val property: StateFlow<PropertyInput> = _property

    private val _selectedRegion = MutableStateFlow<String?>("Seoul")
    val selectedRegion: StateFlow<String?> = _selectedRegion

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _predictionResult = MutableStateFlow<PredictionResult?>(null)
    val predictionResult: StateFlow<PredictionResult?> = _predictionResult

    fun updateProperty(property: PropertyInput) { _property.value = property }
    fun setRegion(region: String?) { _selectedRegion.value = region }

    fun predict() {
        if (!modelService.isLoaded || _isLoading.value) return
        _isLoading.value = true
        val input = _property.value
        val region = _selectedRegion.value

        viewModelScope.launch {
            try {
                val hash = cacheKey(input, region)
                predictionDao.getPredictionByHash(hash)?.let { cached ->
                    _predictionResult.value = cached.toResult()
                    return@launch
                }
                val result = withContext(Dispatchers.Default) {
                    modelService.predict(input, region)
                }
                if (result != null) {
                    _predictionResult.value = result
                    predictionDao.insertPrediction(result.toEntity(hash))
                    predictionDao.deletePredictionsBefore(System.currentTimeMillis() - TTL_MS)
                }
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun reset() {
        _property.value = PropertyInput()
        _selectedRegion.value = "Seoul"
        _predictionResult.value = null
    }

    private fun cacheKey(input: PropertyInput, region: String?): String {
        val raw = "${region ?: "nationwide"}|${input.region}|${input.areaM2}|${input.yearBuilt}"
        val digest = MessageDigest.getInstance("SHA-256").digest(raw.toByteArray())
        return digest.joinToString("") { "%02x".format(it) }
    }

    private fun PredictionEntity.toResult() =
        PredictionResult(predictedPrice, confidenceScore, region, timestamp)

    private fun PredictionResult.toEntity(hash: String) =
        PredictionEntity(
            predictedPrice = predictedPrice,
            confidenceScore = confidenceScore,
            region = region,
            timestamp = timestamp,
            featuresHash = hash,
        )

    private companion object {
        const val TTL_MS = 86_400_000L
    }
}
