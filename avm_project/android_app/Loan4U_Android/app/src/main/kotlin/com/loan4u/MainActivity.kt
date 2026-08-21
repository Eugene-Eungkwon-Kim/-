package com.loan4u

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.fillMaxSize
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.loan4u.ui.PropertyInputViewModel
import com.loan4u.ui.screens.PredictionResultScreen
import com.loan4u.ui.screens.PropertyInputScreen
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    // Activity-scoped so both screens share one instance (prediction flows through).
    private val viewModel: PropertyInputViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Loan4UTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val navController = rememberNavController()
                    NavHost(navController = navController, startDestination = "input") {
                        composable("input") {
                            PropertyInputScreen(
                                viewModel = viewModel,
                                onPredictionSuccess = { navController.navigate("result") },
                            )
                        }
                        composable("result") {
                            PredictionResultScreen(
                                viewModel = viewModel,
                                onNewValuation = {
                                    viewModel.reset()
                                    navController.popBackStack("input", inclusive = false)
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun Loan4UTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()
    MaterialTheme(colorScheme = colors, content = content)
}
