package com.loan4u.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.loan4u.ui.PropertyInputViewModel

@Composable
fun PredictionResultScreen(
    onNewValuation: () -> Unit,
    viewModel: PropertyInputViewModel = hiltViewModel(),
) {
    val predictionResult by viewModel.predictionResult.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Valuation Result") })
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (predictionResult != null) {
                val result = predictionResult!!

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        Text(
                            "Estimated Price",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )

                        Text(
                            "₩${String.format("%,d", result.predictedPrice)}",
                            fontSize = 42.sp,
                            fontWeight = FontWeight.Bold,
                        )

                        Divider(modifier = Modifier.fillMaxWidth())

                        ConfidenceIndicator(result.confidenceScore)

                        Divider(modifier = Modifier.fillMaxWidth())

                        InfoRow("Region", result.region)
                        InfoRow(
                            "Predicted",
                            java.text.SimpleDateFormat("MMM dd, HH:mm").format(result.timestamp),
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        viewModel.resetForm()
                        onNewValuation()
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                ) {
                    Text("New Valuation")
                }
            } else {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(Icons.Default.Info, contentDescription = null, modifier = Modifier.size(48.dp))
                    Text("No prediction available", style = MaterialTheme.typography.bodyLarge)
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(onClick = onNewValuation) {
                        Text("Go Back")
                    }
                }
            }
        }
    }
}

@Composable
private fun ConfidenceIndicator(score: Double) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Confidence", style = MaterialTheme.typography.labelMedium)
            Text(
                String.format("%.1f%%", score * 100),
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
            )
        }

        LinearProgressIndicator(
            progress = { score.toFloat() },
            modifier = Modifier
                .fillMaxWidth()
                .height(8.dp),
            color = confidenceColor(score),
        )
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Text(value, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun confidenceColor(score: Double): Color = when {
    score >= 0.8 -> Color.Green
    score >= 0.6 -> Color.Yellow
    else -> Color(0xFFFFA500)
}
