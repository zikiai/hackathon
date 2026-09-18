export { getRecords, renderStatistics, statisticsText, recommendation } from './view.js';
import {renderModelEvidence} from '../../model-evidence.js';
export const config = {
  name:'Rail corrugation', short:'Rail', icon:'route', status:'Pipeline implemented',
  input:'One or more recording CSVs', format:'10,000 rows × 129 columns per recording',
  output:'Normal / Side I / Side II', title:'Possible Side I corrugation',
  finding:'The model identifies a pattern associated with Side I corrugation in this recording.',
  scope:'Recording-level finding. Exact track location is not supplied.',
  next:'Review the recording and corroborating inspection evidence.',
  why:'Side I and Side II are dataset condition labels, not geographic locations or car identifiers.',
  evidence:'Shared-side Random Forest: training-validation macro F1 0.8278. False positives and missed faults remain possible.',
  file:'rail-example-01.csv'
};
export function renderMethod(){return renderModelEvidence('rail');}
