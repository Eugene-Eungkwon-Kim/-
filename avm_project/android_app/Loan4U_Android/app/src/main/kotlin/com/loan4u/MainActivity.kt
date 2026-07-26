package com.loan4u

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.loan4u.ui.screens.PropertyInputScreen
import com.loan4u.ui.screens.PredictionResultScreen
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            Loan4UTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    val navController = rememberNavController()

                    NavHost(navController = navController, startDestination = "input") {
                        composable("input") {
                            PropertyInputScreen(
                                onPredictionSuccess = {
                                    navController.navigate("result")
                                },
                            )
                        }
                        composable("result") {
                            PredictionResultScreen(
                                onNewValuation = {
                                    navController.navigate("input")
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
    MaterialTheme(
        colorScheme = if (true) MaterialTheme.colorScheme else MaterialTheme.colorScheme,
    ) {
        Surface(modifier = Modifier.fillMaxSize()) {
            content()
        }
    }
}
