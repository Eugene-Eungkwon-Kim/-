package com.loan4u.ui.screens

import androidx.compose.foundation.layout.*
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
import com.loan4u.ui.PropertyInputViewModel
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PredictionResultScreen(
    viewModel: PropertyInputViewModel,
    onNewValuation: () -> Unit,
) {
    val result by viewModel.predictionResult.collectAsState()

    Scaffold(topBar = { TopAppBar(title = { Text("Valuation Result") }) }) { padding ->
        Column(
            modifier = Modifier.padding(padding).fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            val r = result
            if (r != null) {
                Card(Modifier.fillMaxWidth()) {
                    Column(
                        Modifier.fillMaxWidth().padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        Text("Estimated Price", style = MaterialTheme.typography.labelMedium)
                        Text("₩${"%,d".format(r.predictedPrice)}", fontSize = 40.sp, fontWeight = FontWeight.Bold)
                        Divider()
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Confidence")
                            Text("%.0f%%".format(r.confidenceScore * 100), fontWeight = FontWeight.SemiBold)
                        }
                        LinearProgressIndicator(
                            progress = { r.confidenceScore.toFloat() },
                            modifier = Modifier.fillMaxWidth().height(8.dp),
                            color = confidenceColor(r.confidenceScore),
                        )
                        Divider()
                        InfoRow("Region", r.region)
                        InfoRow("Predicted", SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault()).format(Date(r.timestamp)))
                    }
                }
                Spacer(Modifier.height(24.dp))
                Button(onClick = onNewValuation, modifier = Modifier.fillMaxWidth().height(48.dp)) {
                    Text("New Valuation")
                }
            } else {
                Text("No prediction available")
                Spacer(Modifier.height(16.dp))
                Button(onClick = onNewValuation) { Text("Go Back") }
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.labelMedium)
        Text(value, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
    }
}

private fun confidenceColor(score: Double): Color = when {
    score >= 0.8 -> Color(0xFF2E7D32)
    score >= 0.5 -> Color(0xFFF9A825)
    else -> Color(0xFFEF6C00)
}
