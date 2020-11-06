from prov.model import ProvDocument, parse_xsd_datetime
from provstore.bundle_manager import BundleManager


# Document exceptions
class DocumentException(Exception):
    pass


class AbstractDocumentException(DocumentException):
    def __init__(self):
        self.message = "Unsaved documents cannot be read"


class EmptyDocumentException(DocumentException):
    def __init__(self):
        self.message = "There is no data associated with this document"


class ImmutableDocumentException(DocumentException):
    def __init__(self):
        self.message = "Cannot change document instance reference"


# API Document model
class Document(object):
    """
    ProvStore Document model.

    .. note::
        This class should not be instantiated manually but should be accessed via
        :py:meth:`provstore.api.Api.document` like so::

          >>> from provstore.api import Api
          >>> api = Api()
          >>> api.document
          <provstore.document.Document at ...>
    """
    def __init__(self, api):
        self._api = api
        self._id = None

        self._name = None
        self._public = None
        self._owner = None
        self._created_at = None
        self._views = None

        self._bundles = None

        self._prov = None

    def __eq__(self, other):
        if not isinstance(other, Document):
            return False

        return self._api == other._api and self.id == other.id

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        if self.abstract:
            return "<Abstract Document %s>" % self.__hash__()
        else:
            return "%s/documents/%i" % (self._api.base_url, self.id)

    # Abstract methods
    def create(self, prov_document, prov_format=None, refresh=False, **props):
        """
        Create a document on ProvStore.

        :param prov_document: The document to be stored
        :param prov_format: The format of the document provided
        :param bool refresh: Whether or not to load back the document after saving
        :param dict props: Properties for this document [**name** (required), **public** = False]
        :return: This document itself but with a reference to the newly stored document
        :type prov_document: :py:class:`prov.model.ProvDocument` or :py:class:`str`
        :type prov_format: :py:class:`str` or None
        :rtype: :py:class:`provstore.document.Document`
        :raises ImmutableDocumentException: If this instance already refers to another document
        """
        if not self.abstract:
            raise ImmutableDocumentException()

        if isinstance(prov_document, ProvDocument):
            self._prov = prov_document

            prov_format = "json"
            prov_document = prov_document.serialize()

        self._id = self._api.post_document(prov_document, prov_format, **props)['id']

        if refresh:
            self.refresh()
        else:
            self._bundles = BundleManager(self._api, self)

        return self

    save = create

    def set(self, document_id):
        """
        Associate this document with a ProvStore document without making any calls to the API.
        :param int document_id: ID of the document on ProvStore
        :return: self
        """
        if not self.abstract:
            raise ImmutableDocumentException()
        self._id = document_id

        return self

    def get(self, document_id):
        """
        Associate this model with a document on ProvStore.

        Example::
          >>> api = Api()
          >>> api.document.get(148)
          https://openprovenance.org/store/api/v0/documents/148
          >>> api.id
          148
          >>> api.name
          ex:bundles1-sep

        :param document_id: The document ID on ProvStore
        :return: self
        """
        if not self.abstract:
            raise ImmutableDocumentException()

        return self.read(document_id)

    # Instance methods
    def read(self, document_id=None):
        """
        Load the document contents and metadata from the server.

        The following are equivalent::
          >>> api = Api()
          >>> api.set(148).read()
          >>> api.get(148)

        :param document_id: (optional) Set the document ID if this is an abstract document.
        :return: self
        """
        self.read_prov(document_id)
        self.read_meta()
        return self

    def refresh(self):
        """
        Update information about the document from ProvStore.

        :return: self
        """

        # We don't alias so that users cannot specify document_id here
        return self.read()

    def read_prov(self, document_id=None):
        """
        Load the provenance of this document

        .. note::
           This method is called automatically if needed when the :py:meth:`prov` property is accessed. Manual use of
           this method is unusual.

        :param document_id: (optional) set the document id if this is an :py:meth:`abstract` document
        :return: :py:class:`prov.model.ProvDocument
        """
        if document_id:
            if not self.abstract:
                raise ImmutableDocumentException()
            self._id = document_id

        if self.abstract:
            raise AbstractDocumentException()

        self._prov = self._api.get_document_prov(self.id)
        return self._prov

    def read_meta(self, document_id=None):
        """
        Load metadata associated with the document

        .. note::
           This method is called automatically if needed when a property is first accessed. You will not normally have
           to use this method manually.

        :param document_id: (optional) set the document id if this is an :py:meth:`abstract` document
        :return: self
        """
        if document_id:
            if not self.abstract:
                raise ImmutableDocumentException()
            self._id = document_id

        if self.abstract:
            raise AbstractDocumentException()

        metadata = self._api.get_document_meta(self.id)

        self._name = metadata['document_name']
        self._public = metadata['public']
        self._owner = metadata['owner']
        self._created_at = parse_xsd_datetime(metadata['created_at'])
        self._views = metadata['views_count']

        self._bundles = BundleManager(self._api, self)

        return self

    def add_bundle(self, prov_bundle, identifier):
        """
        Verbose method of adding a bundle.

        Can also be done as:
          >>> api = Api()
          >>> document = api.document.get(148)
          >>> document.bundles['identifier'] = prov_bundle

        :param prov_bundle: The bundle to be added
        :param str identifier: URI or QName for this bundle
        :type prov_bundle: :py:class:`prov.model.ProvDocument` or :py:class:`str`
        """
        if self.abstract:
            raise AbstractDocumentException()

        self._api.add_bundle(self.id, prov_bundle.serialize(), identifier)

    @property
    def bundles(self):
        """
        :return: This document's bundle manager
        :rtype: :py:class:`provstore.bundle_manager.BundleManager`
        """
        if self.abstract:
            raise AbstractDocumentException()

        return self._bundles

    def delete(self):
        """
        Remove the document and all of its bundles from ProvStore.

        .. warning::
           Cannot be undone.
        """
        if self.abstract:
            raise AbstractDocumentException()

        self._api.delete_document(self.id)
        self._id = None

        return True

    @property
    def id(self):
        """
        Unique ID of the document as defined by ProvStore. Used in :py:meth:`get` and :py:meth:`set`
        """
        return self._id

    @property
    def abstract(self):
        """
        True if this document doesn't reference a ProvStore document yet
        """
        return self.id is None

    @property
    def name(self):
        """
        Name of document as seen on ProvStore
        """
        if self._name:
            return self._name
        elif not self.abstract:
            return self.read_meta()._name

        raise EmptyDocumentException()

    @property
    def public(self):
        """
        Is this document visible to anyone?
        """
        if self._public:
            return self._public
        elif not self.abstract:
            return self.read_meta()._public

        raise EmptyDocumentException()

    @property
    def owner(self):
        """
        Username of document creator
        """
        if self._owner:
            return self._owner
        elif not self.abstract:
            return self.read_meta()._owner

        raise EmptyDocumentException()

    @property
    def created_at(self):
        """
        :return: When the document was created
        :rtype: :py:class:`datetime.datetime`
        """
        if self._created_at:
            return self._created_at
        elif not self.abstract:
            return self.read_meta()._created_at

        raise EmptyDocumentException()

    @property
    def views(self):
        """
        Number of views this document has received on ProvStore
        """
        if self._views:
            return self._views
        elif not self.abstract:
            return self.read_meta()._views

        raise EmptyDocumentException()

    @property
    def url(self):
        """
        URL of document on ProvStore

        :Example:
          >>> stored_document.url
          'https://openprovenance.org/store/documents/148'
        """
        if not self.abstract:
            return "%s/documents/%i" % ("/".join(self._api.base_url.split("/")[:-2]), self.id)

    @property
    def prov(self):
        """
        Provenance stored for this document as :py:class:`prov.model.ProvDocument`
        """
        if self._prov:
            return self._prov
        elif not self.abstract:
            return self.read_prov()

        raise EmptyDocumentException()
