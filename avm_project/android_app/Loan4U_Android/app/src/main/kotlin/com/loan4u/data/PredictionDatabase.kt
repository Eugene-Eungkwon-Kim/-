package com.loan4u.data

import android.content.Context
import androidx.room.*
import com.loan4u.services.PredictionResult
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Entity(tableName = "predictions")
data class PredictionEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val predictedPrice: Int,
    val confidenceScore: Double,
    val region: String,
    val timestamp: Long,
    val featuresHash: String,
)

@Dao
interface PredictionDao {
    @Insert
    suspend fun insertPrediction(prediction: PredictionEntity)

    @Query("SELECT * FROM predictions WHERE featuresHash = :hash LIMIT 1")
    suspend fun getPredictionByHash(hash: String): PredictionEntity?

    @Query("SELECT * FROM predictions ORDER BY timestamp DESC LIMIT 50")
    suspend fun getRecentPredictions(): List<PredictionEntity>

    @Query("DELETE FROM predictions WHERE timestamp < :cutoffTime")
    suspend fun deletePredictionsBefore(cutoffTime: Long)
}

@Database(entities = [PredictionEntity::class], version = 1, exportSchema = false)
abstract class PredictionDatabase : RoomDatabase() {
    abstract fun predictionDao(): PredictionDao

    companion object {
        private var instance: PredictionDatabase? = null

        fun getInstance(context: Context): PredictionDatabase {
            return instance ?: synchronized(this) {
                Room.databaseBuilder(context, PredictionDatabase::class.java, "loan4u_db")
                    .build()
                    .also { instance = it }
            }
        }
    }
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Singleton
    @Provides
    fun providePredictionDatabase(@ApplicationContext context: Context): PredictionDatabase {
        return PredictionDatabase.getInstance(context)
    }

    @Singleton
    @Provides
    fun providePredictionDao(database: PredictionDatabase): PredictionDao {
        return database.predictionDao()
    }
}
