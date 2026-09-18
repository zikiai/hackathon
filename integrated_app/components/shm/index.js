export { getRecords, renderStatistics, statisticsText, recommendation } from './view.js';
export const config={name:'Structural health',short:'Structure',icon:'activity',status:'Model available',input:'One or more stress records',format:'CSV: one numeric column, no header. Training records contain 581,120 readings.',output:'One cumulative fatigue-damage estimate per record'};
