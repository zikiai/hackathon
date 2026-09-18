// Full saved pipeline outputs, independent of the small UI reference selection.
export const predictionDownloads = {
  shm: {filename:'shm_predictions.csv',url:'./downloads/shm_predictions.csv',count:16,unit:'test files',columns:['file_id','prediction']},
  door: {filename:'door_predictions.csv',url:'./downloads/door_predictions.csv',count:38,unit:'movements',columns:['start_time','end_time','prediction']},
  rail: {filename:'rail_predictions.csv',url:'./downloads/rail_predictions.csv',count:68,unit:'test files',columns:['file_id','prediction']}
};
