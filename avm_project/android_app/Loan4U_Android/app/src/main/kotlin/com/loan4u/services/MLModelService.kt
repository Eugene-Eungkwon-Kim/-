package com.loan4u.services

import android.content.Context
import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MLModelService @Inject constructor(private val context: Context) : ViewModel() {
    private val _isLoaded = MutableStateFlow(false)
    val isLoaded: StateFlow<Boolean> = _isLoaded

    private val _loadingError = MutableStateFlow<String?>(null)
    val loadingError: StateFlow<String?> = _loadingError

    private var nationalwideInterpreter: Interpreter? = null
    private val regionalInterpreters = mutableMapOf<String, Interpreter>()
    private val regionNames = listOf("Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon")

    init {
        loadModels()
    }

    private fun loadModels() {
        try {
            loadNationwideModel()
            loadRegionalModels()
            _isLoaded.value = true
        } catch (e: Exception) {
            _loadingError.value = "Failed to load models: ${e.message}"
        }
    }

    private fun loadNationwideModel() {
        val buffer = loadModelFile("KR_nationwide_lite_int8.tflite")
        nationalwideInterpreter = Interpreter(buffer)
    }

    private fun loadRegionalModels() {
        for (region in regionNames) {
            val filename = "KR_${region.lowercase()}_lite_int8.tflite"
            runCatching {
                val buffer = loadModelFile(filename)
                regionalInterpreters[region] = Interpreter(buffer)
            }
        }
    }

    private fun loadModelFile(filename: String): MappedByteBuffer {
        val assetFileDescriptor = context.assets.openFd(filename)
        val inputStream = FileInputStream(assetFileDescriptor.fileDescriptor)
        val fileChannel = inputStream.channel
        val startOffset = assetFileDescriptor.startOffset
        val declaredLength = assetFileDescriptor.declaredLength
        return fileChannel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }

    fun predict(features: Map<String, Float>, region: String? = null): PredictionResult? {
        val interpreter = region?.let { regionalInterpreters[it] } ?: nationalwideInterpreter
        interpreter ?: return null

        return try {
            val inputArray = Array(1) { FloatArray(22) }
            val sortedFeatures = features.toSortedMap()
            sortedFeatures.values.forEachIndexed { idx, value ->
                inputArray[0][idx] = value
            }

            val outputArray = Array(1) { FloatArray(1) }
            interpreter.run(inputArray, outputArray)

            val predictedPrice = (outputArray[0][0] * 1_000_000).toLong().toInt()
            val confidenceScore = (1.0 - (Math.abs(predictedPrice - 500_000_000) / 1_000_000_000.0)).coerceIn(0.0, 1.0)

            PredictionResult(
                predictedPrice = predictedPrice,
                confidenceScore = confidenceScore,
                region = region ?: "Nationwide",
                timestamp = System.currentTimeMillis()
            )
        } catch (e: Exception) {
            _loadingError.value = "Prediction failed: ${e.message}"
            null
        }
    }

    override fun onCleared() {
        super.onCleared()
        nationalwideInterpreter?.close()
        regionalInterpreters.values.forEach { it.close() }
    }
}

data class PredictionResult(
    val predictedPrice: Int,
    val confidenceScore: Double,
    val region: String,
    val timestamp: Long
)
