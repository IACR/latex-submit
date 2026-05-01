import glob
from lxml import etree
import simplejson

# These need to be skipped until we can resolve the dependent schemas locally somehow.
skip_schemas = {
    "schemas/crossref4.4.0.xsd", "schemas/crossref4.4.1.xsd",
    "schemas/crossref4.4.2.xsd", "schemas/unixref1.0.xsd",
    "schemas/unixref1.1.xsd", "schemas/crossref4.3.5.xsd",
    "schemas/crossref4.3.4.xsd", "schemas/crossref4.3.6.xsd",
    "schemas/crossref4.3.7.xsd", "schemas/crossref4.3.8.xsd",
    "schemas/crossref4.3.3.xsd", "schemas/crossref_query_output2.0.xsd",
    "schemas/JATS-journalpublishing1-elements.xsd",
    "schemas/JATS-journalpublishing1-mathml3-elements.xsd",
    "schemas/JATS-journalpublishing1-mathml3.xsd",
    "schemas/JATS-journalpublishing1-3d2-mathml3.xsd",
    "schemas/JATS-journalpublishing1-3d2-mathml3-elements.xsd",
    "schemas/standard-modules/mathml3/mathml3-common.xsd",
    "schemas/standard-modules/mathml3/mathml3-content.xsd",
    "schemas/standard-modules/mathml3/mathml3-presentation.xsd",
    "schemas/standard-modules/mathml3/mathml3-strict-content.xsd",
    "schemas/standard-modules/mathml3/mathml3.xsd"
}


class DTDResolver(etree.Resolver):
    "Resolver to load local schema files."

    def __init__(self):
        # namespace to tuples of (filename, content)
        self.ns = {}
        with open("schemas/index.json", "r") as f:
            entries = simplejson.load(f)
            for entry in entries:
                filename = "schemas/" + entry["filename"]
                with open(filename, "r") as content:
                    self.ns[entry["namespace"]] = (filename, content.read())

    def resolve(self, url, id, context):
        # Only resolve locally those that use http.
        # Local files still need to be found locally.
        if url.startswith("http:") or url.startswith("https:"):
            print("Resolving URL '%s'" % url)
            return self.resolve_string(self.ns[url][1])
        else:
            # Pass, another resolver will try.
            return None


parser = etree.XMLParser(load_dtd=True)
resolver = DTDResolver()
parser.resolvers.add(resolver)


def validate_schema(filename):
    "Validate that a schema file conforms to XSD schema."

    ok = True

    root = etree.parse(filename)
    print("Validating schema file: %s" % filename)

    try:
        schema = etree.XMLSchema(root)
        print("Validated %s" % filename)
    except Exception as e:
        print("Failed! %s" % filename)
        ok = False

    return ok


def applicable_schema_from_doc(root):
    "Given a document, retrieve the applicable schema."
    schema_location = root.getroot().attrib[
        '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'].split(
            ' ')[0]
    (filename, _) = resolver.ns[schema_location]
    schema_root = etree.parse(filename)
    return etree.XMLSchema(schema_root)


def validate_example(filename):
    "Validate that an example file conforms to schemas."

    ok = True
    print("Validating example file: %s" % filename)
    try:
        root = etree.parse(filename, parser)
        schema = applicable_schema_from_doc(root)
        schema.assertValid(root)
    except Exception as e:
        print("Failed to validate %s " % filename)
        print(e.args)
        ok = False

    return ok


def all_schema_filenames():
    "Return all schema filenames found."
    return glob.glob("schemas/**.xsd")


def all_examples():
    "Return all example filenames found."
    return glob.glob("examples/**.xml")


def run_all_checks():
    ok = True

    print("Ignoring schema checks for:")
    for item in skip_schemas:
        print(item)

    print("Check schemas...")
    for filename in all_schema_filenames():
        if filename not in skip_schemas:
            result = validate_schema(filename)
            ok = ok and result

    print("Check examples against schemas...")
    for filename in all_examples():
        result = validate_example(filename)
        ok = ok and result

    if ok:
        print("All checks passed.")
    else:
        print("There were failures.")
    return ok


if __name__ == "__main__":
    if not run_all_checks():
        exit(1)
