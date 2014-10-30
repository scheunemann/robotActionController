#Source: http://stackoverflow.com/questions/14878706/merge-xml-files-with-nested-elements-without-external-libraries
from xml.etree import ElementTree as et

class XMLCombiner(object):
    def __init__(self, roots):
        assert len(roots) > 0, 'No Roots!'
        # save all the roots, in order, to be processed later
        self.roots = roots

    def combine(self):
        for r in self.roots[1:]:
            # combine each element with the first one, and update that
            self.roots[0].attrib.update( r.attrib )
            self.combine_element(self.roots[0], r)

        # return a new root representing the merged files
        return et.fromstring(et.tostring(self.roots[0]))

    def __mappingKey(self, element):
        attrs = ",".join(["%s:%s" % (k, element.attrib[k]) for k in element.attrib.keys()])
        return "%s:(%s)" % (element.tag, attrs)

    def combine_element(self, one, other):
        """
        This function recursively updates either the text or the children
        of an element if another element is found in `one`, or adds it
        from `other` if not found.
        """

        # Create a mapping from tag name to element, as that's what we are filtering with
        # As attribute values are used to distinguish elements, use them in the key
        mapping = {self.__mappingKey(el): el for el in one}
        for el in other:
            key = self.__mappingKey(el)
            if len(el) == 0:
                # Not nested
                try:
                    mapping[key].text = el.text
                except KeyError:
                    # An element with this name is not in the mapping
                    mapping[key] = el
                    # Add it
                    one.append(el)
            else:
                try:
                    # Recursively process the element, and update it in the same way
                    self.combine_element(mapping[key], el)
                except KeyError:
                    # Not in the mapping
                    mapping[key] = el
                    # Just add it
                    one.append(el)
