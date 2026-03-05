#!/bin/bash

if ! command -v gh &> /dev/null; then
  echo "GitHub CLI (gh) is not installed. Please install it to proceed."
  exit 1
fi

current_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $current_version"

read -p "New version: " version

if [ -z "$version" ]; then
  echo "Version cannot be empty."
  exit 1
fi

# Update version in pyproject.toml and __init__.py
sed -i '' "s/^version = \".*\"/version = \"$version\"/" pyproject.toml
sed -i '' "s/^__version__ = \".*\"/__version__ = \"$version\"/" rincon/__init__.py

git add pyproject.toml rincon/__init__.py
git commit -m "release v$version"
git push origin main

git tag v$version -m "Release version $version"
git push origin v$version

gh release create v$version --generate-notes

echo "Release v$version created. The publish workflow will upload to PyPI."
