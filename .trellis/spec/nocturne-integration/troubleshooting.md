# Nocturne Memory Integration - Troubleshooting Guide

> **Purpose**: Common issues and solutions for Nocturne Memory MCP integration

## Quick Diagnostics

### Check Nocturne Availability

```bash
# Test if Nocturne database is accessible
python3 -c "
from nocturne_client import NocturneClient
client = NocturneClient()
print(f'Database path: {client._db_path}')
print(f'Available: {client.is_available()}')
"
```

### Check Configuration

```bash
# Verify nocturne.yaml configuration
cat .trellis/config/nocturne.yaml

# Check environment variable
echo $NOCTURNE_DB_PATH
```

### Test Hooks

```bash
# Test session-start.py (check for <nocturne> section)
python3 .claude/hooks/session-start.py 2>&1 | grep -A5 "<nocturne>"

# Test inject-subagent-context.py
echo '{"tool_name": "Task", "tool_input": {"subagent_type": "implement", "prompt": "test"}}' | \
  python3 .claude/hooks/inject-subagent-context.py | grep -o "Nocturne"
```

## Common Issues

### Issue: Nocturne Database Not Found

**Symptom**:
```
Database path: ~/.nocturne/memory.db
Available: False
```

**Causes**:
1. Nocturne MCP server not installed
2. Database file doesn't exist
3. Wrong database path in configuration

**Solutions**:

1. **Install Nocturne MCP**:
   ```bash
   # Follow Nocturne MCP installation instructions
   # Typically involves installing from npm or pip
   ```

2. **Create Database Directory**:
   ```bash
   mkdir -p ~/.nocturne
   touch ~/.nocturne/memory.db
   ```

3. **Update Configuration**:
   ```yaml
   # .trellis/config/nocturne.yaml
   db_path: "/correct/path/to/memory.db"
   ```

4. **Set Environment Variable**:
   ```bash
   export NOCTURNE_DB_PATH="/path/to/memory.db"
   echo 'export NOCTURNE_DB_PATH="/path/to/memory.db"' >> ~/.bashrc
   ```

### Issue: Permission Denied

**Symptom**:
```
Error: unable to open database file
Permission denied: ~/.nocturne/memory.db
```

**Solutions**:

1. **Check File Permissions**:
   ```bash
   ls -la ~/.nocturne/memory.db
   ```

2. **Fix Permissions**:
   ```bash
   chmod 644 ~/.nocturne/memory.db
   chmod 755 ~/.nocturne
   ```

3. **Check Directory Ownership**:
   ```bash
   sudo chown -R $USER:$USER ~/.nocturne
   ```

### Issue: Session Start Slow

**Symptom**: Session startup takes > 100ms

**Diagnosis**:
```bash
# Time the session start hook
time python3 .claude/hooks/session-start.py > /dev/null

# Check Nocturne query time
python3 -c "
import time
from nocturne_client import NocturneClient
client = NocturneClient()
start = time.time()
results = client.query_patterns('trellis', 'patterns/python/%', max_results=10)
print(f'Query time: {(time.time() - start) * 1000:.2f}ms')
print(f'Results: {len(results)}')
"
```

**Solutions**:

1. **Reduce auto_load_patterns**:
   ```yaml
   # .trellis/config/nocturne.yaml
   auto_load_patterns:
     - domain: "trellis"
       path_prefix: "patterns/python/%"
       max_results: 5  # Reduce from 10
   ```

2. **Increase Priority Threshold**:
   ```yaml
   # Only load critical and high priority memories
   priority_threshold: 1
   ```

3. **Disable Nocturne Temporarily**:
   ```yaml
   enabled: false
   ```

### Issue: Hooks Not Injecting Nocturne Context

**Symptom**: No `<nocturne>` section in session start output

**Diagnosis**:
```bash
# Check if Nocturne client is importable
python3 -c "from nocturne_client import NocturneClient; print('OK')"

# Check hook output
python3 .claude/hooks/session-start.py 2>&1 | head -50
```

**Solutions**:

1. **Verify nocturne_client.py exists**:
   ```bash
   ls -la .trellis/scripts/nocturne_client.py
   ```

2. **Check for import errors**:
   ```bash
   python3 .trellis/scripts/nocturne_client.py
   ```

3. **Verify config exists**:
   ```bash
   ls -la .trellis/config/nocturne.yaml
   ```

### Issue: URI Parsing Errors

**Symptom**:
```
ValueError: Invalid URI format: 'invalid-uri'
```

**Solutions**:

1. **Check URI format**:
   ```python
   from nocturne_client import NocturneClient
   # Valid formats:
   NocturneClient.parse_nocturne_uri("trellis://patterns/python")
   NocturneClient.parse_nocturne_uri("core://agent")
   ```

2. **Common mistakes to avoid**:
   - Missing `://` separator
   - Uppercase domain names (will be lowercased)
   - Trailing slashes (will be stripped)

### Issue: promote-to-nocturne.py Not Working

**Symptom**: Script runs but memories not created in Nocturne

**Diagnosis**:
```bash
# Test with --list first
python3 .trellis/scripts/promote-to-nocturne.py --list

# Check if learning exists
python3 .trellis/scripts/promote-to-nocturne.py --learning 1
```

**Solutions**:

1. **Check memory file exists**:
   ```bash
   ls -la .trellis/memory/learnings.md
   cat .trellis/memory/learnings.md
   ```

2. **Verify entry format**:
   ```markdown
   ## 2026-02-17: Title Here

   **Category**: pattern

   Content here...
   ```

3. **Note**: The script prepares parameters but requires MCP to actually create memories. Use the output with Claude Code's `create_memory` tool.

### Issue: sync-trellis-to-nocturne.py Shows All Skipped

**Symptom**: All entries show "SKIP (exists)" in dry-run

**Solutions**:

1. **Check existing memories**:
   ```python
   from nocturne_client import NocturneClient
   client = NocturneClient()
   results = client.query_patterns("trellis", "projects/researchclaw/%")
   for r in results:
       print(r.uri)
   ```

2. **Force overwrite if needed**:
   ```bash
   python3 .trellis/scripts/sync-trellis-to-nocturne.py --force
   ```

3. **Use different URIs**:
   Edit the entry titles to generate different URIs

## Debug Logging

### Enable Verbose Output

Modify scripts to add debug output:

```python
# Add to nocturne_client.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Hook Execution

Add logging to hooks:

```python
# In session-start.py
def get_nocturne_context(trellis_dir: Path) -> str:
    print(f"DEBUG: Checking Nocturne at {trellis_dir}", file=sys.stderr)
    # ... rest of function
```

### Trace Database Queries

```python
# Enable SQLite query logging
import sqlite3
sqlite3.enable_callback_tracebacks(True)
```

## Environment-Specific Issues

### WSL Issues

**Issue**: Database path resolution problems

**Solution**:
```yaml
# Use Windows-style paths in WSL if needed
db_path: "/mnt/c/Users/username/.nocturne/memory.db"
```

### macOS Issues

**Issue**: Permission issues with ~/.nocturne

**Solution**:
```bash
# Create directory with correct permissions
mkdir -p ~/.nocturne
chmod 755 ~/.nocturne
```

### Windows Issues

**Issue**: Path separator issues

**Solution**:
```python
# Use Pathlib for cross-platform paths
from pathlib import Path
db_path = Path.home() / ".nocturne" / "memory.db"
```

## Performance Tuning

### Slow Query Performance

1. **Add Database Index** (if you control the database):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_paths_domain_path ON paths(domain, path);
   CREATE INDEX IF NOT EXISTS idx_paths_priority ON paths(priority);
   ```

2. **Reduce Query Scope**:
   ```python
   # More specific prefix = faster query
   client.query_patterns("trellis", "patterns/python/error-handling/%")
   ```

3. **Limit Results**:
   ```python
   client.query_patterns("trellis", "patterns/python/%", max_results=5)
   ```

### High Memory Usage

1. **Close connections explicitly**:
   ```python
   client = NocturneClient()
   try:
       results = client.query_patterns(...)
   finally:
       client.close()
   ```

2. **Use context managers**:
   ```python
   with NocturneClient() as client:
       results = client.query_patterns(...)
   ```

## Getting Help

### Gather Diagnostic Information

```bash
# Run this script and share the output
python3 << 'EOF'
import sys
import os
from pathlib import Path

print("=== Nocturne Diagnostics ===")
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")
print(f"NOCTURNE_DB_PATH: {os.environ.get('NOCTURNE_DB_PATH', 'not set')}")

try:
    from nocturne_client import NocturneClient
    client = NocturneClient()
    print(f"Database path: {client._db_path}")
    print(f"Database exists: {Path(client._db_path).exists()}")
    print(f"Database available: {client.is_available()}")
except Exception as e:
    print(f"Error importing nocturne_client: {e}")

print("\n=== Config ===")
config_path = Path(".trellis/config/nocturne.yaml")
if config_path.exists():
    print(config_path.read_text())
else:
    print("Config file not found")
EOF
```

### Report Issues

When reporting issues, include:
1. Output of diagnostic script above
2. Error messages (full traceback)
3. Steps to reproduce
4. Expected vs actual behavior

## FAQ

**Q: Do I need Nocturne MCP installed for Trellis to work?**
A: No. The integration gracefully degrades if Nocturne is unavailable.

**Q: Can I use a different database path?**
A: Yes. Set `NOCTURNE_DB_PATH` environment variable or edit `nocturne.yaml`.

**Q: How do I know if Nocturne is being used?**
A: Check session start output for `<nocturne>` section, or agent prompts for Nocturne hints.

**Q: Can I disable Nocturne integration?**
A: Yes. Set `enabled: false` in `.trellis/config/nocturne.yaml`.

**Q: Why aren't my learnings appearing in Nocturne?**
A: The promotion scripts prepare parameters but don't directly write to Nocturne. Use the MCP `create_memory` tool with the output parameters.
