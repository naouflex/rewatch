import SchemaBrowser from "@/components/queries/SchemaBrowser";
import QueryEditor from "@/components/queries/QueryEditor";
import DatabricksSchemaBrowser from "./databricks/DatabricksSchemaBrowser";
import ApiSchemaBrowser from "./api/ApiSchemaBrowser";

import { registerEditorComponent, getEditorComponents, QueryEditorComponents } from "./editorComponents";

// default
registerEditorComponent(QueryEditorComponents.SCHEMA_BROWSER, SchemaBrowser);
registerEditorComponent(QueryEditorComponents.QUERY_EDITOR, QueryEditor);

// databricks
registerEditorComponent(QueryEditorComponents.SCHEMA_BROWSER, DatabricksSchemaBrowser, [
  "databricks",
  "databricks_internal",
]);

// yaml api runners with categorized endpoint schema
registerEditorComponent(QueryEditorComponents.SCHEMA_BROWSER, ApiSchemaBrowser, ["coingecko", "defillama"]);

export { getEditorComponents };
