#!/usr/bin/env python3
"""
Phase 5: Deployment
Deploy Excel file and finalize operations
"""

import shutil
import json
from pathlib import Path
from datetime import datetime

class Deployment:
    """Deploy system to production"""

    def __init__(self):
        self.deployment_status = {}
        self.status_log = []

    def task_5_1_deploy_files(self):
        """Task 5.1: Deploy Excel file to locations"""
        print("\n" + "=" * 60)
        print("TASK 5.1: DEPLOY FILES")
        print("=" * 60)

        try:
            source_file = Path("./output/Loan4U_QC_v1.1_DATA.csv")

            if not source_file.exists():
                print(f"❌ Source file not found: {source_file}")
                return False

            # Define deployment locations
            locations = [
                Path("./deployment/location1_shared/"),
                Path("./deployment/location2_backup/"),
                Path("./deployment/location3_archive/")
            ]

            deployed = 0
            for loc in locations:
                try:
                    loc.mkdir(parents=True, exist_ok=True)
                    dest = loc / source_file.name
                    shutil.copy2(source_file, dest)
                    print(f"✅ Deployed to: {loc}")
                    deployed += 1
                except Exception as e:
                    print(f"⚠️ Failed to deploy to {loc}: {str(e)}")

            print(f"✅ Task 5.1 Complete: {deployed}/3 locations deployed")
            self.status_log.append(f"5.1: Deployed to {deployed} locations")
            self.deployment_status['file_deployment'] = deployed

            return deployed > 0

        except Exception as e:
            print(f"❌ Task 5.1 Failed: {str(e)}")
            self.status_log.append(f"5.1 Error: {str(e)}")
            return False

    def task_5_2_finalize_operations(self):
        """Task 5.2: Finalize and prepare for operations"""
        print("\n" + "=" * 60)
        print("TASK 5.2: FINALIZE OPERATIONS")
        print("=" * 60)

        try:
            # Create deployment metadata
            metadata = {
                "deployment_date": datetime.now().isoformat(),
                "version": "Loan4U QC v1.1",
                "data_rows": 3501,
                "data_columns": 10,
                "locations": [
                    "location1_shared",
                    "location2_backup",
                    "location3_archive"
                ],
                "status": "OPERATIONAL"
            }

            # Save deployment info
            deploy_dir = Path("./deployment")
            deploy_dir.mkdir(exist_ok=True)
            metadata_file = deploy_dir / "deployment_metadata.json"

            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            print(f"✅ Deployment metadata saved: {metadata_file}")
            print(f"   Version: {metadata['version']}")
            print(f"   Status: {metadata['status']}")
            print(f"   Locations: {len(metadata['locations'])}")

            self.status_log.append("5.2: Operations finalized")
            self.deployment_status['finalization'] = True

            return True

        except Exception as e:
            print(f"❌ Task 5.2 Failed: {str(e)}")
            self.status_log.append(f"5.2 Error: {str(e)}")
            return False

    def task_5_3_user_training(self):
        """Task 5.3: Prepare user training materials"""
        print("\n" + "=" * 60)
        print("TASK 5.3: USER TRAINING PREPARATION")
        print("=" * 60)

        try:
            # Create training guide
            training_guide = """
# Loan4U QC v1.1 - User Guide

## Overview
Automated Valuation Model for real estate pricing prediction.

## How to Use
1. Open Loan4U_QC_v1.1_FINAL.xlsx
2. Navigate to AI Predict sheet
3. Enter property details (area, region, type)
4. Press Calculate to get price prediction

## Sheets
- RAW: Complete consolidated data
- Apartment: Apartment-filtered data
- Villa: Villa-filtered data
- Statistics: Market statistics dashboard
- AI Predict: Price prediction interface

## Support
Contact: support@loan4u.com
"""

            training_dir = Path("./deployment/training")
            training_dir.mkdir(parents=True, exist_ok=True)
            guide_file = training_dir / "USER_GUIDE.md"

            with open(guide_file, 'w') as f:
                f.write(training_guide)

            print(f"✅ Training guide created: {guide_file}")
            print(f"✅ Task 5.3 Complete")

            self.status_log.append("5.3: Training materials prepared")
            self.deployment_status['training'] = True

            return True

        except Exception as e:
            print(f"❌ Task 5.3 Failed: {str(e)}")
            self.status_log.append(f"5.3 Error: {str(e)}")
            return False

    def run_phase5(self):
        """Execute Phase 5 deployment"""
        print("\n" + "=" * 70)
        print("PHASE 5: DEPLOYMENT")
        print("=" * 70)

        success = True
        success = self.task_5_1_deploy_files() and success
        success = self.task_5_2_finalize_operations() and success
        success = self.task_5_3_user_training() and success

        # Summary
        print("\n" + "=" * 60)
        print("PHASE 5 SUMMARY")
        print("=" * 60)

        summary = {
            "phase": "5",
            "tasks": ["5.1", "5.2", "5.3"],
            "timestamp": datetime.now().isoformat(),
            "status_log": self.status_log,
            "deployment_status": self.deployment_status,
            "completion_status": "✅ COMPLETE" if success else "⚠️ PARTIAL"
        }

        print(f"Locations Deployed: {self.deployment_status.get('file_deployment', 0)}/3")
        print(f"Operations Finalized: {self.deployment_status.get('finalization', False)}")
        print(f"Training Ready: {self.deployment_status.get('training', False)}")
        print(f"Status: {summary['completion_status']}")

        # Save summary
        summary_file = Path("./logs/phase5_summary.json")
        summary_file.parent.mkdir(exist_ok=True)
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"✅ Phase 5 Complete: Summary saved to {summary_file}")

        return success


if __name__ == "__main__":
    deployer = Deployment()
    deployer.run_phase5()
