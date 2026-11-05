// Validates data/ (or VIBE_DATA=fixtures) against the schema without building the site.
// Exit code 1 and one line per problem when a file is malformed.
import { loadDataset } from '../src/lib/data.ts';

const d = loadDataset();
const withMetrics = d.projects.filter((p) => p.metrics).length;
if (d.errors.length) {
  console.error(`${d.errors.length} problems in ${d.dir}:`);
  for (const e of d.errors) console.error(`  ${e}`);
  process.exit(1);
}
console.log(`${d.dir}: ${d.projects.length} projects valid (${withMetrics} with metrics), ${d.mscs.length} MSCs`);
