package com.loan4u.services

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import com.loan4u.features.FeatureEngineering
import com.loan4u.features.PropertyInput
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.nio.FloatBuffer
import javax.inject.Inject
import javax.inject.Singleton

data class PredictionResult(
    val predictedPrice: Int,
    val confidenceScore: Double,
    val region: String,
    val timestamp: Long,
)

/**
 * Loads the shipped ONNX models with ONNX Runtime for Android. Both platforms
 * load the identical `.onnx` files verified by the Python contract test — no
 * TFLite/CoreML conversion step.
 */
@Singleton
class MLModelService @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    @Volatile var isLoaded: Boolean = false
        private set
    @Volatile var loadingError: String? = null
        private set

    private var env: OrtEnvironment? = null
    private val sessions = mutableMapOf<String, OrtSession>()
    private val modelKeys = listOf("nationwide", "seoul", "busan", "gyeonggi", "daegu", "incheon")

    private val regionMape = mapOf(
        "seoul" to 0.0947, "busan" to 0.0948, "gyeonggi" to 0.0994,
        "daegu" to 0.1094, "incheon" to 0.0950, "nationwide" to 0.8148,
    )

    /** Loads all models off the main thread. Safe to call once at startup. */
    suspend fun load() = withContext(Dispatchers.IO) {
        try {
            val environment = OrtEnvironment.getEnvironment()
            env = environment
            modelKeys.forEach { key ->
                context.assets.open("models/KR_${key}_lite.onnx").use { stream ->
                    val bytes = stream.readBytes()
                    sessions[key] = environment.createSession(bytes, OrtSession.SessionOptions())
                }
            }
            check(sessions.containsKey("nationwide")) { "nationwide model missing" }
            isLoaded = true
        } catch (e: Exception) {
            loadingError = "Model load failed: ${e.message}"
        }
    }

    fun predict(input: PropertyInput, region: String?): PredictionResult? {
        val key = region?.lowercase() ?: "nationwide"
        val session = sessions[key] ?: sessions["nationwide"] ?: return null
        val environment = env ?: return null

        return try {
            val vector = FeatureEngineering.buildVector(input)
            val tensor = OnnxTensor.createTensor(
                environment,
                FloatBuffer.wrap(vector),
                longArrayOf(1, vector.size.toLong()),
            )
            tensor.use { t ->
                session.run(mapOf("float_input" to t)).use { output ->
                    @Suppress("UNCHECKED_CAST")
                    val raw = (output[0].value as Array<FloatArray>)[0][0]
                    if (raw <= 0f) return null
                    PredictionResult(
                        predictedPrice = raw.toInt(),
                        confidenceScore = (1.0 - (regionMape[key] ?: 0.5)).coerceIn(0.0, 1.0),
                        region = region ?: "Nationwide",
                        timestamp = System.currentTimeMillis(),
                    )
                }
            }
        } catch (e: Exception) {
            loadingError = "Inference failed: ${e.message}"
            null
        }
    }
}
