#!/bin/sh

# Purpose:
# Create a USB drive containing the latest documentation and
# Docker images needed to run Open States and be able to submit GitHub PRs

# Requirements:
# - Git
# - Docker
# - Sphinx and theme (from documentation/requirements.txt)

drivepath="/Volumes/openstates"

if ! cd "$drivepath"; then
	echo "Error: Manually rename the USB drive to \`$(basename "$drivepath")\`"
	echo "Once completed, please re-run this script"
	exit
fi

if ! [ -z "$(ls -A .)" ]; then
	echo "This drive is not empty!"
	echo "Do you wish to overwrite any existing Open States directories on this drive? (y or n)"
	read -p "> " wipedrive
	if [ "$wipedrive" != "y" ]; then
		echo "Did not confirm the deletion of drive contents; exiting script"
		exit
	else
		rm -rf ./openstates
		rm -rf ./docker-images
		rm -rf ./documentation
	fi
fi

# Copy the main Open States repo
git clone git@github.com:openstates/openstates.git

# Locally save the Docker images needed for Open States's Docker Compose services
# Our USB drives are 4 GB in capacity, so to fit the essentials,
# the openstates/openstates.org image is excluded
mkdir docker-images
images="openstates/openstates mongo"
for image in $images; do
	docker pull "${image}"
	# Need to strip the forward slash so they can act as filenames
	filename=$(echo "${image}" | sed 's/\///g')
	docker save --output "./docker-images/${filename}.gz" "${image}:latest"
done

# Get and build the Open States documentation
git clone git@github.com:openstates/documentation.git
cd documentation
make html
cd ..

# Add USB drive documentation
echo "How to use this Open States USB drive
===

This USB drive contains a recent build of all necessary resources to run Open States scrapers, so that you don't need to wait for them to download.

Prerequisites:

- Git
- Docker

## Copy the Open States repository to your machine

Copy the \`openstates\` directory to your local machine's storage. This is a full Git repository, and is ready for you to commit new changes.

## Load the Docker images

Make the Docker images available on your local machine using:

\`\`\`bash
for f in ${drivepath}/docker-images/*.gz; do
	docker load --input \"\${f}\"
done
\`\`\`

Now you can continue with the [Getting Started documentation](http://docs.openstates.org/en/latest/contributing/getting-started.html) as if you had just finished running \`docker-compose build openstates\`.

## Read the documentation

The documentation [is available online](http://docs.openstates.org), but is also on this drive. Simply open \`./documentation/_build/html/index.html\` in a web browser.
" > ./README.md
