
## commands used to generate chunked content
```
./chunked/gen.sh "cfhd" "12.5_25_50" "t16" "2023-09-01"
./chunked/gen.sh "chh1" "12.5_25_50" "t2" "2025-01-15"
./chunked/gen.sh "cud1" "12.5_25_50" "t22" "2025-01-15"
./chunked/gen.sh "clg1" "12.5_25_50" "t42" "2025-01-15"
./chunked/gen.sh "chd1" "12.5_25_50" "t62" "2025-01-15"
```


## generating chunked content

1. create the MPD corresponding to the target test vector configuration and name it according to the media profile.
2. run the `gen.sh` script with the corresponding arguments
