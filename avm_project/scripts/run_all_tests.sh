#!/bin/bash
set -e

PROJECT_DIR="avm_project"
BUILD_DIR="build/phase14.3_tests"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "=========================================="
echo "Phase 14.3: Automated Test Execution"
echo "=========================================="
echo "Date: $(date)"
echo "Directory: $PROJECT_DIR"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"

# 1. Python cross-platform validation
echo "1. Running Python cross-platform validation..."
if python3 scripts/cross_platform_validation.py; then
    echo "   ✅ Python validation passed" | tee -a "$BUILD_DIR/test_summary.log"
else
    echo "   ❌ Python validation failed" | tee -a "$BUILD_DIR/test_summary.log"
    exit 1
fi
echo ""

# 2. iOS tests (if Xcode available)
if command -v xcodebuild &> /dev/null; then
    echo "2. Running iOS unit tests..."
    cd $PROJECT_DIR

    if xcodebuild -workspace Loan4U.xcworkspace \
      -scheme Loan4U \
      -configuration Debug \
      -sdk iphonesimulator \
      -destination 'platform=iOS Simulator,name=iPhone 15 Pro' \
      test 2>&1 | tee ../$BUILD_DIR/ios_test_${TIMESTAMP}.log; then
        echo "   ✅ iOS tests passed" | tee -a ../$BUILD_DIR/test_summary.log
    else
        echo "   ❌ iOS tests failed" | tee -a ../$BUILD_DIR/test_summary.log
    fi
    cd ..
else
    echo "2. Skipping iOS tests (Xcode not available on this platform)"
fi
echo ""

# 3. Android tests (if Gradle available)
if command -v gradle &> /dev/null || [ -f "$PROJECT_DIR/gradlew" ]; then
    echo "3. Running Android unit tests..."
    cd $PROJECT_DIR

    if ./gradlew testDebugUnitTest --info 2>&1 | tee ../$BUILD_DIR/android_test_${TIMESTAMP}.log; then
        echo "   ✅ Android tests passed" | tee -a ../$BUILD_DIR/test_summary.log
    else
        echo "   ❌ Android tests failed" | tee -a ../$BUILD_DIR/test_summary.log
    fi
    cd ..
else
    echo "3. Skipping Android tests (Gradle not available)"
fi
echo ""

# 4. Summary
echo "=========================================="
echo "✅ Test Execution Complete"
echo "=========================================="
echo "Report location: $BUILD_DIR/"
echo ""
echo "Files generated:"
ls -lh "$BUILD_DIR"/ 2>/dev/null || echo "No test logs yet"
echo ""
echo "Summary:"
cat "$BUILD_DIR/test_summary.log" 2>/dev/null || echo "No summary available"
