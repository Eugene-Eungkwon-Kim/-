package com.loan4u.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.loan4u.features.HouseType
import com.loan4u.features.PropertyInput
import com.loan4u.ui.PropertyInputViewModel

@Composable
fun PropertyInputScreen(
    onPredictionSuccess: () -> Unit,
    viewModel: PropertyInputViewModel = hiltViewModel(),
) {
    val property by viewModel.property.collectAsState()
    val selectedRegion by viewModel.selectedRegion.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val predictionResult by viewModel.predictionResult.collectAsState()

    LaunchedEffect(predictionResult) {
        if (predictionResult != null) {
            onPredictionSuccess()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Property Valuation") },
                navigationIcon = { Icon(Icons.Default.Home, contentDescription = null) },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            PropertyDetailsSection(property) { updated ->
                viewModel.updateProperty(updated)
            }

            LocationFeaturesSection(property) { updated ->
                viewModel.updateProperty(updated)
            }

            AmenitiesSection(property) { updated ->
                viewModel.updateProperty(updated)
            }

            PropertyTypeSection(property) { updated ->
                viewModel.updateProperty(updated)
            }

            RegionSelectionSection(selectedRegion) { region ->
                viewModel.setRegion(region)
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = { viewModel.predict() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                enabled = !isLoading,
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp))
                } else {
                    Text("Predict Price")
                }
            }
        }
    }
}

@Composable
private fun PropertyDetailsSection(
    property: PropertyInput,
    onUpdate: (PropertyInput) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Property Details", style = MaterialTheme.typography.titleMedium)

            LabeledSlider(
                label = "Area (㎡): ${property.areaSqm}",
                value = property.areaSqm.toFloat(),
                onValueChange = { onUpdate(property.copy(areaSqm = it.toInt())) },
                valueRange = 20f..500f,
            )

            LabeledSlider(
                label = "Year Built: ${property.yearBuilt}",
                value = property.yearBuilt.toFloat(),
                onValueChange = { onUpdate(property.copy(yearBuilt = it.toInt())) },
                valueRange = 1980f..2024f,
            )

            LabeledSlider(
                label = "Floor Level: ${property.floorLevel}",
                value = property.floorLevel.toFloat(),
                onValueChange = { onUpdate(property.copy(floorLevel = it.toInt())) },
                valueRange = 1f..30f,
            )

            LabeledSlider(
                label = "Total Floors: ${property.floorsTotal}",
                value = property.floorsTotal.toFloat(),
                onValueChange = { onUpdate(property.copy(floorsTotal = it.toInt())) },
                valueRange = 1f..50f,
            )

            LabeledSlider(
                label = "Bedrooms: ${property.bedrooms}",
                value = property.bedrooms.toFloat(),
                onValueChange = { onUpdate(property.copy(bedrooms = it.toInt())) },
                valueRange = 1f..8f,
            )

            LabeledSlider(
                label = "Bathrooms: ${property.bathrooms}",
                value = property.bathrooms.toFloat(),
                onValueChange = { onUpdate(property.copy(bathrooms = it.toInt())) },
                valueRange = 1f..5f,
            )
        }
    }
}

@Composable
private fun LocationFeaturesSection(
    property: PropertyInput,
    onUpdate: (PropertyInput) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Location Features", style = MaterialTheme.typography.titleMedium)

            LabeledSlider(
                label = "Distance to Subway (m): ${property.distanceSubwayM}",
                value = property.distanceSubwayM.toFloat(),
                onValueChange = { onUpdate(property.copy(distanceSubwayM = it.toInt())) },
                valueRange = 0f..5000f,
            )

            LabeledSlider(
                label = "Crime Rate: ${String.format("%.2f", property.crimeRate)}",
                value = property.crimeRate.toFloat(),
                onValueChange = { onUpdate(property.copy(crimeRate = it.toDouble())) },
                valueRange = 0f..1f,
            )

            LabeledSlider(
                label = "Population Density: ${property.populationDensity.toInt()}",
                value = property.populationDensity.toFloat(),
                onValueChange = { onUpdate(property.copy(populationDensity = it.toDouble())) },
                valueRange = 5000f..30000f,
            )
        }
    }
}

@Composable
private fun AmenitiesSection(
    property: PropertyInput,
    onUpdate: (PropertyInput) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Amenities", style = MaterialTheme.typography.titleMedium)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Elevator")
                Switch(checked = property.hasElevator, onCheckedChange = { onUpdate(property.copy(hasElevator = it)) })
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Parking")
                Switch(checked = property.hasParking, onCheckedChange = { onUpdate(property.copy(hasParking = it)) })
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("Garden")
                Switch(checked = property.hasGarden, onCheckedChange = { onUpdate(property.copy(hasGarden = it)) })
            }
        }
    }
}

@Composable
private fun PropertyTypeSection(
    property: PropertyInput,
    onUpdate: (PropertyInput) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Property Type", style = MaterialTheme.typography.titleMedium)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                HouseType.values().forEach { type ->
                    FilterChip(
                        selected = property.houseType == type,
                        onClick = { onUpdate(property.copy(houseType = type)) },
                        label = { Text(type.name) },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
    }
}

@Composable
private fun RegionSelectionSection(
    selectedRegion: String?,
    onRegionChange: (String?) -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Region (Optional)", style = MaterialTheme.typography.titleMedium)

            val regions = listOf("Nationwide", "Seoul", "Busan", "Gyeonggi", "Daegu", "Incheon")
            regions.forEach { region ->
                FilterChip(
                    selected = (if (region == "Nationwide") selectedRegion == null else selectedRegion == region),
                    onClick = { onRegionChange(if (region == "Nationwide") null else region) },
                    label = { Text(region) },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun LabeledSlider(
    label: String,
    value: Float,
    onValueChange: (Float) -> Unit,
    valueRange: ClosedFloatingPointRange<Float>,
) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall)
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = valueRange,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}
