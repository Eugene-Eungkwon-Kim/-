"""특성 스키마"""

def load_schema():
    return {
        '면적': float,
        '지역': int,
        '건축년도': int,
        '층수': int,
        '방_개수': int,
        '욕실_개수': int,
        '엘리베이터': int,
        '주차장': int,
    }
