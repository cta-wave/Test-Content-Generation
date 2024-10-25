batch_dir=2024-09-25
python run-all.py -q -b=$batch_dir ./content_files/chh1_splice_main.csv ./profiles/chh1_splice_main.csv > batch.log
python run-all.py -q -b=$batch_dir ./content_files/chh1_splice_ad.csv ./profiles/chh1_splice_ad.csv >> batch.log
python run-all.py -b=$batch_dir ./content_files/chh1.csv ./profiles/chh1.csv >> batch.log
python run-all.py -b=$batch_dir ./content_files/chd1.csv ./profiles/chd1.csv >> batch.log
