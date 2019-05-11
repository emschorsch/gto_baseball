#!/bin/bash

lfs_install () {
    # Install git-lfs and pull the data files
    wget https://github.com/github/git-lfs/releases/download/v1.1.0/git-lfs-linux-amd64-1.1.0.tar.gz
    tar -zxvf git-lfs-linux-amd64-1.1.0.tar.gz
    export PATH=`pwd`/git-lfs-1.1.0:$PATH
    git config credential.helper store
    echo "https://emschorsch:$GITHUB_USER_TOKEN@github.com" > ~/.git-credentials
    git lfs install
}


ls -ll fixtures
ls -ll cached_fixtures


# use unaliased cp to copy with overwrite from cache
echo 'copying files from cache'
\cp -rf cached_fixtures/* fixtures

echo 'install git lfs'
lfs_install

echo 'git reset'
git reset
# git add -f fixtures/*

echo 'git status'
git status
echo 'git branch'
git branch

echo 'pulling from git-lfs'
git lfs status
git lfs pull

git checkout fixtures/


echo 'updating cache'
rm -rf cached_fixtures
cp -r fixtures/ ./cached_fixtures


ls -ll fixtures
ls -ll cached_fixtures

bash --version
