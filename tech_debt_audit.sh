#!/bin/bash

echo "=== TECHNICAL DEBT AUDIT ==="
echo ""
echo "1. CODE QUALITY ISSUES"
echo "  - Missing type hints in scripts:"
find avm_project/scripts -name "*.py" -type f | while read f; do
  total=$(grep -c "^def " "$f" 2>/dev/null || echo 0)
  hinted=$(grep -c "def.*->.*:" "$f" 2>/dev/null || echo 0)
  if [ "$total" -gt 0 ] && [ "$hinted" -lt "$total" ]; then
    echo "    $(basename $f): $hinted/$total functions have return type hints"
  fi
done

echo ""
echo "2. POTENTIAL DEAD CODE (commented-out blocks)"
find avm_project/scripts -name "*.py" | xargs grep -l "^[[:space:]]*#.*def\|^[[:space:]]*#.*class" | while read f; do
  count=$(grep -c "^[[:space:]]*#.*def\|^[[:space:]]*#.*class" "$f")
  echo "    $(basename $f): $count commented functions/classes"
done

echo ""
echo "3. TEST COVERAGE"
python -m pytest avm_project/tests/ --collect-only -q 2>/dev/null | tail -1
echo "    Run: pytest --cov=avm_project --cov-report=term-missing"

echo ""
echo "4. DOCUMENTATION GAPS"
echo "  - Checking docstrings:"
find avm_project/scripts -name "*.py" -type f | while read f; do
  defs=$(grep -c "^def " "$f" 2>/dev/null || echo 0)
  docs=$(grep -c '"""' "$f" 2>/dev/null || echo 0)
  if [ "$defs" -gt 0 ] && [ "$docs" -lt 2 ]; then
    echo "    $(basename $f): $docs docstring blocks for $defs functions"
  fi
done

echo ""
echo "5. DEPENDENCY ISSUES"
echo "  - Pinned versions:"
grep "==" avm_project/requirements.txt | wc -l
echo "  - Unpinned versions:"
grep -E ">=|<=|~=" avm_project/requirements.txt | wc -l
