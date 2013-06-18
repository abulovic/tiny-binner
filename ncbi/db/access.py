from sqlalchemy.engine import create_engine
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy import Table, MetaData, Column, Integer

from ncbi.db.unity import UnityRecord, UnityCDS
from sqlalchemy.sql.expression import select
from utils.location import Location

_metadata = MetaData()

table_gi_taxid_nuc = Table('gi_taxid_nuc', _metadata,
    Column('gi', Integer, primary_key=True),
    Column('tax_id', Integer),
)

class DbQuery(object):
    '''Serves as a database query utility.'''
    def __init__(self, unity_db_url=None, ncbitax_db_url=None):
        if not unity_db_url:
            unity_db_url = "mysql+mysqldb://root:root@localhost/unity"
        self.unity_db_url = unity_db_url
        if not ncbitax_db_url:
            ncbitax_db_url = "mysql+mysqldb://root:root@localhost/ncbitax"
        self.ncbitax_db_url = ncbitax_db_url
        self._create_sessions()


    def get_record (self, version):
        '''
        Returns the record associated with the given accession.version.
        
        :param version: string - GenBank/EMBL/DDBJ/RefSeq Accesion.Version
        :returns: UnityRecord - record associated with the given 
                  accession.version. None if no record is found
        '''
        sess = self.unity_session()
        try:
            
            records = sess.execute("""
            
                SELECT id, db, version, nucl_gi, taxon, location,
                    protein_id, locus_tag, product, gene, prot_gi
                FROM cds
                WHERE version=:version;
            """,
            {
                'version': version
             })
    
            record = None
    
            for r in records:
                if not record:
                    record = UnityRecord(r['version'])
                cds = UnityCDS(dict(r))
                record.add_cds(cds)

            if record:        
                record.cds.sort(key=lambda x: x.location_min)
        
            return record
        finally:
            self.unity_session.remove()
        

    def get_taxids (self, gis, format=dict):
        '''
        Fetches taxonomy ID for each of the GIs.
        @param gis (list) list of integers representing GIs
        @param format (object type) list or dict.
        @return based on format parameter, returns either list of 
        tax IDs or a dictionary mapping gis to tax ids. List can 
        contain duplicates.
        '''
        
        if not gis:
            return format()
        
        sess = self.ncbitax_session()
        try:
            s = select([table_gi_taxid_nuc.c.gi, table_gi_taxid_nuc.c.tax_id]
                       ).where(table_gi_taxid_nuc.c.gi.in_(gis))
            records = sess.execute(s)
    
            if format == dict:
                gi2taxid_dict = {}
                for (gi, taxid) in records:
                    gi2taxid_dict[int(gi)] = int(taxid)
    
                return gi2taxid_dict
    
            elif format == list:
                taxid_list = []
                for (gi, taxid) in records:
                    taxid_list.append (int(taxid))
    
                return taxid_list
    
            else:
                return None
        finally:
            self.ncbitax_session.remove()
        

    def get_organism_name (self, taxid, name_class='scientific name'):
        ''' 
        Fetches organism name for the speficied taxonomy ID.
        @param taxid (int)  taxonomy ID
        @param name_class (str) scientific name, common name, genbank common
        name, authority
        @return organism name (str)
        '''
        
        sess = self.ncbitax_session()
        try:
            
            records = sess.execute("""
                SELECT name_txt 
                FROM ncbi_names 
                WHERE name_class=:nameClass AND tax_id=:taxId;
            """,
            {
                'nameClass': name_class,
                'taxId': taxid
             })
    
            record = records.first()
    
            if record:
                return record['name_txt']
                    
            return None
        
        finally:
            self.ncbitax_session.remove()

    def get_organism_rank (self, query, by_name=False):
        '''
        Fetches organism rank. Query can be done using organism name 
        or organism tax ID. 
        @param query (str/int) depends on by_name parameter
        @param by_name (boolean) true if query should be done using organism
        name instead of tax ID.
        @return (str) organism taxonomy rank
        '''
        if by_name:
            tax_id = self.get_organism_taxid(query)
        else:
            tax_id = query
        if not tax_id:
            return None

        tax_id = int(tax_id)
        
        sess = self.ncbitax_session()
        try:
            
            records = sess.execute("""
                SELECT rank 
                FROM ncbi_nodes 
                WHERE tax_id=:taxId;
            """,
            {
                'taxId': tax_id
             })
    
            record = records.first()
    
            if record:
                return record['rank']
                    
            return None
        
        finally:
            self.ncbitax_session.remove()
        
  
    def get_organism_taxid (self, organism_name, name_class='scientific name'):
        '''
        Fetches organism taxid for the specified organism name.
        @param organism_name (str) organism nam
        @return taxid (int)
        '''
        sess = self.ncbitax_session()
        try:
            
            records = sess.execute("""
                SELECT tax_id 
                FROM ncbi_names 
                WHERE name_class=:nameClass AND name_txt=:nameText;
            """,
            {
                'nameClass': name_class,
                'nameText': organism_name
             })
    
            record = records.first()
    
            if record:
                return int(record['tax_id'])
                    
            return None
        
        finally:
            self.ncbitax_session.remove()


    def _create_sessions(self):
        ''' Creates database sessions '''
        unity_engine = create_engine (self.unity_db_url, echo=False, 
                                convert_unicode=True, encoding='utf-8',
                                pool_recycle=3600)
        unity_session = scoped_session(sessionmaker(
                        bind=unity_engine, autocommit=False, autoflush=False))
        
        self.unity_session = unity_session
        
        ncbitax_engine = create_engine (self.ncbitax_db_url, echo=False, 
                                convert_unicode=True, encoding='utf-8',
                                pool_recycle=3600)
        
        ncbitax_session = scoped_session(sessionmaker(
                        bind=ncbitax_engine, autocommit=False, autoflush=False))

        self.ncbitax_session = ncbitax_session

        
