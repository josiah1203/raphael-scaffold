# Git history migration (optional)

Calliope and hblabs-sonoma are archived with `ARCHIVED.md` pointers. To preserve git history in target repos:

```bash
# Requires: pip install git-filter-repo

# Example: migrate calliope-vcs history into raphael-workspaces
git clone /Users/josiah/calliope /tmp/calliope-filter
cd /tmp/calliope-filter
git filter-repo --path packages/calliope-vcs/ --path packages/calliope-delta/
cd /Users/josiah/Projects/raphael-workspaces
git remote add calliope /tmp/calliope-filter
git fetch calliope
git merge --allow-unrelated-histories calliope/main -m "chore: import calliope-vcs history"

# Repeat per package using the map in calliope/ARCHIVED.md
```

For most teams, the `ARCHIVED.md` migration map plus fresh commits in `raphael-*` repos is sufficient.
