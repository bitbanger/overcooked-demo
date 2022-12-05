mkdir server/HTNAgent
cp -r ~/Code/HTNAgent server/HTNAgent
mkdir server/py_rete
cp -r ~/Code/py_rete server/py_rete
mkdir server/AL_Core
cp -r ~/Code/AL_Core server/AL_Core
mkdir server/tutorenvs
cp -r ~/Code/tutorenvs server/tutorenvs

if [[ $1 = prod* ]];
then
    echo "production"
    export BUILD_ENV=production

    # Completely re-build all images from scatch without using build cache
    # docker-compose build --no-cache
    # docker-compose up --force-recreate -d
    docker-compose up --build
else
    echo "development"
    export BUILD_ENV=development
    # Uncomment the following line if there has been an updated to overcooked-ai code
    # docker-compose build --no-cache

    # Force re-build of all images but allow use of build cache if possible
    docker-compose up --build
fi
