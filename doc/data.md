## Dealing with Pomagma data

Pomagma keeps data at the S3 bucket [pomagma](http://pomagma.s3.amazonaws.com).
Although the bucket is publicly accessible, the requester must bay for
bandwidth, so you need to be logged in to get data.

To pull existing data from a snapshot on, say, 2015-05-17:

    cd data
    python -m pomagma.store pull atlas.2015-05-17/  # trailing slash needed!
    python -m pomagma.store snapshot atlas.2015-05-17 atlas
    rm -rf atlas.2015-05-17
    cd ..

To snapshot and push data to the bucket on, say, 2015-08-01:

    cd data
    python -m pomagma.store snapshot atlas atlas.2015-08-01
    python -m pomagma.store push atlas.2015-08-01
    rm -rf atlas.2015-08-01
    cd ..
