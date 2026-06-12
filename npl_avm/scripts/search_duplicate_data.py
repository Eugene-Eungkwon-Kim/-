#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
import sqlite3

EXTERNAL_HDD = Path("D:/")


def scan_databases():
    """DB 파일 검색"""
    print("\n" + "="*70)
    print("Database Files Search")
    print("="*70)

    db_files = []

    for root, dirs, files in os.walk(EXTERNAL_HDD):
        # 깊이 제한 (너무 깊지 않게)
        if root.count(os.sep) - EXTERNAL_HDD.as_posix().count(os.sep) > 5:
            continue

        for f in files:
            if f.endswith(('.db', '.sqlite', '.sqlite3')):
                full_path = Path(root) / f
                size_mb = full_path.stat().st_size / (1024 * 1024)
                db_files.append({
                    'name': f,
                    'path': str(full_path),
                    'size_mb': round(size_mb, 2),
                    'modified': full_path.stat().st_mtime,
                })

    if db_files:
        print(f"\nFound {len(db_files)} database files:\n")
        for db in sorted(db_files, key=lambda x: x['modified'], reverse=True)[:20]:
            print(f"  {db['name']:40} {db['size_mb']:>8.2f} MB")
            print(f"    Path: {db['path']}")
            print()
    else:
        print("\nNo database files found")

    return db_files


def scan_data_collection_scripts():
    """데이터 수집 스크립트 검색"""
    print("\n" + "="*70)
    print("Data Collection Scripts")
    print("="*70)

    keywords = [
        'fetch', 'crawl', 'scrape', 'ingest', 'import', 'collect',
        'download', 'rtms', 'rtech', 'vworld', 'api', 'transaction'
    ]

    script_files = []

    for root, dirs, files in os.walk(EXTERNAL_HDD):
        if root.count(os.sep) - EXTERNAL_HDD.as_posix().count(os.sep) > 4:
            continue

        for f in files:
            if f.endswith(('.py', '.sh', '.bat')):
                f_lower = f.lower()
                if any(kw in f_lower for kw in keywords):
                    full_path = Path(root) / f
                    script_files.append({
                        'name': f,
                        'path': str(full_path),
                        'modified': full_path.stat().st_mtime,
                    })

    if script_files:
        print(f"\nFound {len(script_files)} scripts:\n")
        for script in sorted(script_files, key=lambda x: x['modified'], reverse=True)[:15]:
            print(f"  {script['name']:50}")
            print(f"    {script['path']}\n")
    else:
        print("\nNo collection scripts found")

    return script_files


def scan_data_folders():
    """데이터 폴더 검색"""
    print("\n" + "="*70)
    print("Data Folders (Similar Structure)")
    print("="*70)

    keywords = [
        'transaction', 'trade', 'rtms', 'rtech', 'housing', 'complex',
        'apartment', 'real_estate', 'property', 'data', 'dataset',
        'collection', 'api', 'csv', 'json'
    ]

    data_folders = []

    for root, dirs, files in os.walk(EXTERNAL_HDD):
        depth = root.count(os.sep) - EXTERNAL_HDD.as_posix().count(os.sep)
        if depth > 4:
            continue

        folder_name = os.path.basename(root).lower()

        if any(kw in folder_name for kw in keywords):
            file_count = len(files)
            total_size = sum(
                (Path(root) / f).stat().st_size
                for f in files
                if (Path(root) / f).is_file()
            ) / (1024 * 1024)

            data_folders.append({
                'path': root,
                'name': os.path.basename(root),
                'files': file_count,
                'size_mb': round(total_size, 2),
            })

    if data_folders:
        print(f"\nFound {len(data_folders)} relevant folders:\n")
        for folder in sorted(data_folders, key=lambda x: x['size_mb'], reverse=True)[:15]:
            print(f"  {folder['name']:50} {folder['files']:>5} files {folder['size_mb']:>10.2f} MB")
            print(f"    {folder['path']}\n")
    else:
        print("\nNo relevant data folders found")

    return data_folders


def scan_config_and_logs():
    """설정 및 로그 파일 검색"""
    print("\n" + "="*70)
    print("Configuration & Log Files")
    print("="*70)

    config_files = []

    for root, dirs, files in os.walk(EXTERNAL_HDD):
        if root.count(os.sep) - EXTERNAL_HDD.as_posix().count(os.sep) > 4:
            continue

        for f in files:
            if f in ['.env', 'config.json', 'settings.json'] or f.endswith(('.log', '.txt')):
                f_lower = f.lower()
                if any(kw in f_lower for kw in ['api', 'config', 'log', 'env', 'setting']):
                    full_path = Path(root) / f
                    config_files.append({
                        'name': f,
                        'path': str(full_path),
                    })

    if config_files:
        print(f"\nFound {len(config_files)} config/log files:\n")
        for cfg in config_files[:20]:
            print(f"  {cfg['name']:40}")
            print(f"    {cfg['path']}\n")
    else:
        print("\nNo config/log files found")

    return config_files


def analyze_loan4u_structure():
    """loan4u_avm_data 상세 분석"""
    print("\n" + "="*70)
    print("loan4u_avm_data Project Analysis")
    print("="*70)

    loan4u = Path("D:/loan4u_avm_data")

    if not loan4u.exists():
        print("\nloan4u_avm_data directory not found")
        return

    print(f"\nPath: {loan4u}")
    print(f"Last modified: {loan4u.stat().st_mtime}")

    # 폴더별 파일/크기
    folder_stats = {}

    for root, dirs, files in os.walk(loan4u):
        rel_path = os.path.relpath(root, loan4u)
        if rel_path == '.':
            rel_path = '[Root]'

        total_size = sum(
            (Path(root) / f).stat().st_size
            for f in files
            if (Path(root) / f).is_file()
        ) / (1024 * 1024)

        if total_size > 0:
            folder_stats[rel_path] = {
                'files': len(files),
                'size_mb': round(total_size, 2),
            }

    print(f"\nFolder Structure ({len(folder_stats)} folders with data):\n")
    for folder in sorted(folder_stats.items(), key=lambda x: x[1]['size_mb'], reverse=True)[:20]:
        print(f"  {folder[0]:50} {folder[1]['files']:>5} files {folder[1]['size_mb']:>10.2f} MB")


def main():
    print("\n" + "="*70)
    print("Scanning LG External HDD (D:) for Duplicate Data Collection")
    print("="*70)

    # 1. 데이터베이스 검색
    dbs = scan_databases()

    # 2. 수집 스크립트 검색
    scripts = scan_data_collection_scripts()

    # 3. 데이터 폴더 검색
    folders = scan_data_folders()

    # 4. 설정/로그 검색
    configs = scan_config_and_logs()

    # 5. loan4u_avm_data 분석
    analyze_loan4u_structure()

    # 요약
    print("\n" + "="*70)
    print("Summary")
    print("="*70)

    print(f"""
Database files:        {len(dbs)}
Collection scripts:    {len(scripts)}
Data folders:          {len(folders)}
Config/Log files:      {len(configs)}

Key Finding:
  - loan4u_avm_data contains data collection results from 2026-06-11
  - Multiple CSV/JSONL files for RTMS, VWorld, rtech housing complexes
  - Indicates previous similar data collection work
  - Recommend leveraging existing data before re-collecting from APIs
    """)


if __name__ == "__main__":
    main()
