from  collections       import defaultdict
import os,sys 
sys.path.append(os.getcwd())


class TaxTree ():
    ''' Loads the NCBI taxonomy tree, creates both
        parent-child and child-parent relations,
        enables parent-child relationship testing and
        finding the least common ancestor.
    '''

    def __init__ (self, nodes_file=None):
        ''' Locates the ncbi taxonomy file and sets the important
            taxonomy assignments (such as animalia, bacteria ecc)
            @param location of the ncbi taxonomy tree file
        '''
        
        if not nodes_file:
            nodes_file = self._h_find_taxnode_file()
        self.load(nodes_file) 
        
        #--------- RELEVANT TAXONOMY ASSIGNMENTS ----------#
        self._h_set_relevant_taxonomy_assignments()   
        self._h_map_taxids_to_relevant_tax_nodes()

    def load (self, nodes_file):
        self.parent_nodes   = self._h_get_tax_nodes(nodes_file)
        self.child_nodes    = self._h_populate_child_nodes()
    
    def is_child (self, child_taxid, parent_taxid):
        ''' Test if child_taxid is child node of parent_taxid
            Node is not the child of itself
        '''  
        # check boundary conditions
        if child_taxid == parent_taxid:
            return False
        if parent_taxid == self.root:
            return True
        
        tmp_parent_taxid = child_taxid
        while True:
            if not self.parent_nodes.has_key(tmp_parent_taxid):
                return False
            tmp_parent_taxid = self.parent_nodes[tmp_parent_taxid]
            if tmp_parent_taxid == self.root:
                return False
            if tmp_parent_taxid == parent_taxid:
                return True
            
            

    ############ ############ ##############
    def find_lca (self, taxid_list):
        ''' Finds the lowest common ancestor of
            a list of nodes
        '''
        # each of the visited nodes remembers how many 
        # child nodes traversed it
        self.num_visited        = defaultdict(int)

        current_taxids     = taxid_list
        num_of_nodes       = len(current_taxids)

        # first check if all nodes exist (and sum up blast scores)
        for i in range (0, len(taxid_list)):
            taxid       = taxid_list[i]
            if not self.parent_nodes.has_key(taxid):
                raise Exception ("Key error, no element with id %d." % taxid)

        # now find the lowest common ancestor
        while (True):

            parent_nodes = []
            for taxid in current_taxids:
                # root node must not add itself to parent list
                if   taxid != self.root:    parent_taxid = self.parent_nodes[taxid]
                else:                        parent_taxid = None
                # if parent exists, append him to parent list
                # duplicates ensure that every traversal will count
                if parent_taxid:            parent_nodes.append(parent_taxid)

                self.num_visited[taxid]     += 1
                if self.num_visited[taxid] == num_of_nodes:
                    
                    self.lca_root = taxid
                    self._h_set_visited_nodes() 
                    return taxid
            # refresh current nodes
            current_taxids = parent_nodes

    def get_taxonomy_lineage (self, taxid, db_access):
        '''
        Fetches taxonomy lineage for the organism specified 
        by its taxonomy ID.
        @param taxid (int) taxonomy id
        @param db_access (DbQuery)
        @return lineage (list) list of scientific names of 
        organism that are ancestors of taxid
        '''

        lineage_org_names = []
        lineage_org_taxids = []

        current_node = taxid
        while current_node != self.root:
            lineage_org_taxids.append(current_node)
            if not self.parent_nodes.has_key(current_node):
                break
            current_node = self.parent_nodes[current_node]
        lineage_org_taxids.reverse()

        for taxid in lineage_org_taxids:
            organism_name = db_access.get_organism_name(taxid)
            if organism_name:
                lineage_org_names.append (organism_name)

        return lineage_org_names

    def get_relevant_taxid (self, tax_id):
        return self.tax2relevantTax.get(tax_id, -1)

    def _h_get_tax_nodes        (self, nodes_file):
        '''Loads the taxonomy nodes in a dictionary
           mapping the child to parent node.
        '''
        # file format per line: child_taxid parent_taxid
        with open(nodes_file) as fd:    
            d = dict(self._h_from_parent_child_str (line) for line in fd)
        return d
    
    def _h_from_parent_child_str (self, line):
        '''Loads two integers (taxids) from a line
        '''
        key, sep, value = line.strip().partition(" ")
        if key == value: self.root = int(key)
        return int(key), int(value)
    

    def _h_set_visited_nodes (self):
        ''' Creates class for all the taxids of the nodes visited
            in the LCA tree
        '''
        self.visited_nodes = {}
        for taxid in self.num_visited:
            print self.num_visited[taxid]
            self.visited_nodes[taxid] = TaxNode (
                                                 taxid, 
                                                 self.num_visited[taxid]
                                                 )

    def _h_find_taxnode_file(self):
        ''' Searches recursively through the current
            working directory to find the ncbi_tax_tree file.
        '''
        for root, dirs, files in os.walk (os.getcwd()):
            if 'ncbi_tax_tree' in files:
                return root + ''.join(dirs) + '/ncbi_tax_tree'
            

    def _h_populate_child_nodes (self):
        ''' Populates child nodes from parent to child 
            mapping dictionary
        '''
        child_nodes = defaultdict(list)
        for (child, parent) in self.parent_nodes.items():
            child_nodes[parent].append(child)
        return child_nodes

    def _h_set_relevant_taxonomy_assignments (self):
        ''' Sets some of the more important taxonomy 
            assignments which can help in checking which kingdom
            an organism belongs to.
        '''
        import ncbi.taxonomy.organisms as orgs
        for organism_name in dir(orgs):
            if organism_name.startswith('__'):
                continue
            setattr(self, organism_name, getattr(orgs, organism_name))
        self.potential_hosts = [self.human,
                                self.mouse,
                                self.rats,
                                self.rodents,
                                self.primates,
                                self.animalia,
                                self.green_plants]

        self.microbes =        [self.archea,
                                self.bacteria,
                                self.viruses,
                                self.fungi,
                                self.euglenozoa,
                                self.alveolata,
                                self.amoebozoa,
                                self.fornicata,
                                self.parabasalia,
                                self.heterolobosea,
                                self.viroids,
                                self.stramenopiles,
                                self.cryptomycota,
                                self.entomophthoromycota,
                                self.microsporidia,
                                self.neocallimastigomycota]


    def _h_map_taxids_to_relevant_tax_nodes(self):
        host_nodes = list(self.potential_hosts)
        microbe_nodes = list(self.microbes)

        self.tax2relevantTax = {}       
        for microbe_node in self.microbes:
            microbe_children = self._h_list_all_children(microbe_node)
            for child in microbe_children:
                self.tax2relevantTax[child] = microbe_node

        for host_node in self.potential_hosts:
            host_children = self._h_list_all_children(host_node)
            for child in host_children:
                self.tax2relevantTax[child] = host_node

        tagged_nodes    = self.tax2relevantTax.keys()
        all_nodes       = self.parent_nodes.keys()
        untagged_nodes  = set(all_nodes).difference(tagged_nodes)
        for node in untagged_nodes:
            self.tax2relevantTax[node] = -1

    def _h_list_all_children(self, tax_id):
        if not self.child_nodes.has_key(tax_id):
            return []
        one_step_children = self.child_nodes[tax_id]
        all_children = []
        while (True):
            if not one_step_children:
                break
            new_one_step_children = []
            all_children.extend(one_step_children)
            for child in one_step_children:
                if self.child_nodes.has_key(child):
                    new_one_step_children.extend(self.child_nodes[child])
            one_step_children = new_one_step_children
        return all_children



class TaxNode (object):
    '''
    Contains information relevant to LCA
    taxonomy tree traversal. 
    Relevant informations is:
        - number of times node has been reported in the alignment
        - blast scores for each alignment
        - best  blast score
    '''


    def __init__(self, taxid, num_traversed = None):

        self.taxid              = taxid
        self.num_traversed      = num_traversed

