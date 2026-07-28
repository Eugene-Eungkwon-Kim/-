package com.loan4u.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.loan4u.features.FeatureEngineering
import com.loan4u.ui.PropertyInputViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PropertyInputScreen(
    viewModel: PropertyInputViewModel,
    onPredictionSuccess: () -> Unit,
) {
    val property by viewModel.property.collectAsState()
    val selectedRegion by viewModel.selectedRegion.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val result by viewModel.predictionResult.collectAsState()

    LaunchedEffect(result) { if (result != null) onPredictionSuccess() }

    Scaffold(topBar = { TopAppBar(title = { Text("Property Valuation") }) }) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Region", style = MaterialTheme.typography.titleMedium)
                    val regions = listOf("Nationwide") + FeatureEngineering.regions
                    regions.forEach { region ->
                        val selected = if (region == "Nationwide") selectedRegion == null else selectedRegion == region
                        FilterChip(
                            selected = selected,
                            onClick = { viewModel.setRegion(if (region == "Nationwide") null else region) },
                            label = { Text(region) },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Property", style = MaterialTheme.typography.titleMedium)

                    Text("Area: ${property.areaM2.toInt()} ㎡", style = MaterialTheme.typography.labelLarge)
                    Slider(
                        value = property.areaM2.toFloat(),
                        onValueChange = { viewModel.updateProperty(property.copy(areaM2 = it.toDouble())) },
                        valueRange = 20f..500f,
                    )

                    Text("Year built: ${property.yearBuilt}", style = MaterialTheme.typography.labelLarge)
                    Slider(
                        value = property.yearBuilt.toFloat(),
                        onValueChange = { viewModel.updateProperty(property.copy(yearBuilt = it.toInt())) },
                        valueRange = 1980f..FeatureEngineering.CURRENT_YEAR.toFloat(),
                    )
                }
            }

            Button(
                onClick = { viewModel.predict() },
                enabled = !isLoading,
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                if (isLoading) CircularProgressIndicator(Modifier.size(20.dp)) else Text("Predict Price")
            }
        }
    }
}
