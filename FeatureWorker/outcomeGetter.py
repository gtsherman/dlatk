from featureWorker import FeatureWorker
from fwConstants import *
from fwConstants import _warn, _dbConnectSQLalchemy

class OutcomeGetter(FeatureWorker):
    """Deals with outcome tables"""

    _mysqlNumeric = set(['TINYINT', 'SMALLINT', 'MEDIUMINT','INT', 'INTEGER', 'BIGINT','FLOAT',
                         'DOUBLE', 'DOUBLE PRECISION','REAL','DECIMAL','NUMERIC'])
    _mysqlDate = set(['DATE','DATETIME','TIMESTAMP','TIME','YEAR'])

    @classmethod
    def fromFile(cls, initFile):
        """load variables from file"""
        parser = SafeConfigParser()
        parser.read(initFile)
        corpdb = parser.get('constants','corpdb') if parser.has_option('constants','corpdb') else DEF_CORPDB
        corptable = parser.get('constants','corptable') if parser.has_option('constants','corptable') else DEF_CORPTABLE
        correl_field = parser.get('constants','correl_field') if parser.has_option('constants','correl_field') else DEF_CORREL_FIELD
        mysql_host = parser.get('constants','mysql_host') if parser.has_option('constants','mysql_host') else "localhost"
        message_field = parser.get('constants','message_field') if parser.has_option('constants','message_field') else DEF_MESSAGE_FIELD
        messageid_field = parser.get('constants','messageid_field') if parser.has_option('constants','messageid_field') else DEF_MESSAGEID_FIELD
        lexicondb = parser.get('constants','lexicondb') if parser.has_option('constants','lexicondb') else DEF_LEXICON_DB
        outcome_table = parser.get('constants','outcometable') if parser.has_option('constants','outcometable') else DEF_OUTCOME_TABLE
        outcome_value_fields = [o.strip() for o in parser.get('constants','outcomefields').split(",")] if parser.has_option('constants','outcomefields') else [DEF_OUTCOME_FIELD] # possible list
        outcome_controls = [o.strip() for o in parser.get('constants','outcomecontrols').split(",")] if parser.has_option('constants','outcomecontrols') else DEF_OUTCOME_CONTROLS # possible list
        outcome_interaction = [o.strip() for o in parser.get('constants','outcomeinteraction').split(",")] if parser.has_option('constants','outcomeinteraction') else DEF_OUTCOME_CONTROLS # possible list
        featureMappingTable = parser.get('constants','featlabelmaptable') if parser.has_option('constants','featlabelmaptable') else ''
        featureMappingLex = parser.get('constants','featlabelmaplex') if parser.has_option('constants','featlabelmaplex') else ''
        wordTable = parser.get('constants','wordTable') if parser.has_option('constants','wordTable') else None
        return cls(corpdb=corpdb, corptable=corptable, correl_field=correl_field, mysql_host=mysql_host, message_field=message_field, messageid_field=messageid_field, lexicondb=lexicondb, outcome_table=outcome_table, outcome_value_fields=outcome_value_fields, outcome_controls=outcome_controls, outcome_interaction=outcome_interaction, featureMappingTable=featureMappingTable, featureMappingLex=featureMappingLex, wordTable=wordTable)
    

    def __init__(self, corpdb=DEF_CORPDB, corptable=DEF_CORPTABLE, correl_field=DEF_CORREL_FIELD, mysql_host="localhost", message_field=DEF_MESSAGE_FIELD, messageid_field=DEF_MESSAGEID_FIELD, lexicondb = DEF_LEXICON_DB, outcome_table=DEF_OUTCOME_TABLE, outcome_value_fields=[DEF_OUTCOME_FIELD], outcome_controls = DEF_OUTCOME_CONTROLS, outcome_interaction = DEF_OUTCOME_CONTROLS, featureMappingTable='', featureMappingLex='', wordTable = None):
        super(OutcomeGetter, self).__init__(corpdb, corptable, correl_field, mysql_host, message_field, messageid_field, lexicondb, wordTable = wordTable)
        self.outcome_table = outcome_table

        if isinstance(outcome_value_fields, basestring):
            outcome_value_fields = [outcome_value_fields]

        if outcome_value_fields and len(outcome_value_fields) > 0 and outcome_value_fields[0] == '*':#handle wildcard fields
            newOutcomeFields = []
            for name, typ in self._getTableColumnNameTypes(outcome_table).iteritems():
                typ = re.sub(r'\([0-9\,]*\)\s*$', '', typ)
                if typ.split()[0].upper() in self._mysqlNumeric:
                    newOutcomeFields.append(name)
            outcome_value_fields = newOutcomeFields

        if outcome_controls and len(outcome_controls) > 0 and outcome_controls[0] == '*':#handle wildcard fields
            newOutcomeFields = []
            for name, typ in self._getTableColumnNameTypes(outcome_table).iteritems():
                typ = re.sub(r'\([0-9\,]*\)\s*$', '', typ)
                if typ.split()[0].upper() in self._mysqlNumeric:
                    newOutcomeFields.append(name)
            outcome_controls = newOutcomeFields
        
        self.outcome_value_fields = outcome_value_fields
        self.outcome_controls = outcome_controls
        self.outcome_interaction = outcome_interaction
        self.featureMapping = self.getFeatureMapping(featureMappingTable, featureMappingLex, False)
        self.oneGroupSetForAllOutcomes = False #whether to use groups in common for all outcomes

    def hasOutcomes(self):
        if len(self.outcome_value_fields) > 0:
            return True
        return False

    def copy(self):
        self.__dict__
        newObj = OutcomeGetter(self.corpdb, self.corptable, self.correl_field, self.mysql_host, self.message_field, self.messageid_field)
        for k, v in self.__dict__.iteritems():
            newObj.__dict__[k] = v
        return newObj

    def getFeatureMapping(self, featureMappingTable, featureMappingLex, bracketlabels):
        feat_to_label = {}
        if featureMappingTable:
            feat_to_label = self.getLabelmapFromLabelmapTable(featureMappingTable)
        elif featureMappingLex:
            feat_to_label = self.getLabelmapFromLexicon(featureMappingLex)
            assert( featureMappingTable != featureMappingLex )

        if bracketlabels:
            for feat, label in feat_to_label.iteritems():
                feat_to_label[feat] = '{' + label + '}'
            
        return feat_to_label

    def createOutcomeTable(self,tablename,dataframe, ifExists='fail'):
        eng = _dbConnectSQLalchemy(self.corpdb, self.mysql_host)
        dataframe.to_sql(tablename, eng, index_label = self.correl_field, if_exists = ifExists)
        print "New table created: %s" % tablename

    def getDistinctOutcomeValues(self, outcome = None, includeNull = True, where = ''):
        """returns a list of outcome values"""
        if not outcome:
            outcome = self.outcome_value_fields[0]
        sql = "SELECT DISTINCT %s FROM %s"%(outcome, self.outcome_table)
        if not includeNull or where: 
            wheres = []
            if where: wheres.append(where)
            if not includeNull:
                wheres.append("%s IS NOT NULL" % outcome)
            sql += ' WHERE ' + ' AND '.join(wheres)
        return map(lambda v: v[0], self._executeGetList(sql))

    def getDistinctOutcomeValueCounts(self, outcome = None, requireControls = False, includeNull = True, where = ''):
        """returns a dict of (outcome_value, count)"""
        if not outcome:
            outcome = self.outcome_value_fields[0]
        sql = "SELECT %s, count(*) FROM %s"%(outcome, self.outcome_table)
        if requireControls or not includeNull or where: 
            wheres = []
            if where: wheres.append(where)
            if requireControls:
                for control in self.outcome_controls:
                    wheres.append("%s IS NOT NULL" % control)
            if not includeNull:
                wheres.append("%s IS NOT NULL" % outcome)
            sql += ' WHERE ' + ' AND '.join(wheres)
            
        sql += ' group by %s ' % outcome
        return dict(self._executeGetList(sql))

    def getDistinctOutcomeAndControlValueCounts(self, outcome = None, control = None, includeNull = True, where = ''):
        """returns a dict of (outcome_value, count)"""
        #TODO: muliple controls
        if not outcome:
            outcome = self.outcome_value_fields[0]
        if not control:
            control = self.outcome_controls[0]

        sql = "SELECT %s, %s, count(*) FROM %s"%(outcome, control, self.outcome_table)
        if not includeNull or where: 
            wheres = []
            if where: wheres.append(where)
            if not includeNull:
                wheres.append("%s IS NOT NULL" % outcome)
                wheres.append("%s IS NOT NULL" % control)
            sql += ' WHERE ' + ' AND '.join(wheres)
            
        sql += ' group by %s, %s ' % (outcome, control)
        countDict = dict()
        for (outcome, control, count) in self._executeGetList(sql):
            if not outcome in countDict:
                countDict[outcome] = dict()
            countDict[outcome][control] = count
        return countDict

        
    def getGroupAndOutcomeValues(self, outcomeField = None, where=''):
        """returns a list of (group_id, outcome_value) tuples"""
        if not outcomeField: outcomeField = self.outcome_value_fields[0]
        sql = "select %s, %s from `%s` WHERE %s IS NOT NULL"%(self.correl_field, outcomeField, self.outcome_table, outcomeField)
        if (where): sql += ' AND ' + where
        return self._executeGetList(sql, False)

    def makeContingencyTable(self, featureGetter, featureValueField, outcome_filter_where='', feature_value_group_sum_min=0):
        """makes a contingency table from this outcome value, a featureGetter, and the desired column of the featureGetter, assumes both correl_field's are the same"""
        """follows http://www.artfulsoftware.com/infotree/queries.php at section: Group Column Statistics in Rows"""
        """the only time this uses outcome_value's would be in the outcome_filter_where statement"""
        fg = featureGetter
        distinctFeatureList = fg.getDistinctFeatures() #access single idx
        featZeroDict = dict(fg.getFeatureZeros())
        
        sql = "SELECT %s, "%(fg.correl_field)

        def makeCaseStrings( distinctFeature ):
            df = distinctFeature[0]
            zero = .0000001
            if df in featZeroDict:
                zero = featZeroDict[df]
            df = MySQLdb.escape_string(df)
            if df:#debug
                return "( CASE feat WHEN '%s' THEN %s ELSE %s END ) AS '%s'"%(df, featureValueField, str(zero), df)
            return ''

        case_statements = map(makeCaseStrings, distinctFeatureList)
        sql_cases_features = ", ".join(case_statements) + " "
        #debugN = 1000 #DEBUG
        #_warn( distinctFeatureList[0:debugN] ) #DEBUG
        #sql_cases_features = "".join(case_statements[0:debugN]) #DEBUG
        
        # update the main sql statement to select distinct features as columns
        sql += sql_cases_features

        # filter out the outcomes based on the outcome_filter_where statement
        # an example would be outcome_filter_where = "self.featureValueField is not null and self.featureValueField > 0.50"
        sql_new_outcome_correl_ids = "( SELECT %s FROM %s "%(self.correl_field, self.outcome_table)
        if outcome_filter_where: sql_new_outcome_correl_ids += "WHERE " + outcome_filter_where
        sql_new_outcome_correl_ids += ")"

        # This piece takes care of "users with > 4000 words"
        sql_filtered_feature_table = fg.featureTable
        if feature_value_group_sum_min > 0:
            # Get a sum of "value" for each group_id
            sql_group_ids_and_value_counts = "( SELECT %s, SUM(value) AS value_sum FROM %s GROUP BY %s )"%(fg.correl_field, fg.featureTable, fg.correl_field)
            # Select group_id that have a "value_sum" >= N (input as a function argument; feature_value_group_sum_min)
            sql_group_ids_with_sufficient_value = "( SELECT %s FROM %s AS groupIdsAndSums WHERE value_sum > %s )"%(fg.correl_field, sql_group_ids_and_value_counts, feature_value_group_sum_min)
            # Select the subset of the original fg.featureTable where group_id meets the "value_sum >= N" condition
            sql_filtered_feature_table = "( SELECT featuresOriginal.* FROM %s AS featuresOriginal, %s AS featuresSubset WHERE featuresOriginal.%s = featuresSubset.%s )"%( fg.featureTable, sql_group_ids_with_sufficient_value, fg.correl_field, fg.correl_field)


        # update the feature table to contain only the outcomes from the filtered id's
        sql_filtered_feature_table_2 = "( SELECT filteredFeatures.* FROM %s AS filteredFeatures, %s AS filteredOutcomes WHERE filteredFeatures.%s = filteredOutcomes.%s)"%(sql_filtered_feature_table, sql_new_outcome_correl_ids, fg.correl_field, self.correl_field)

        # finish the original query with the updated feature table
        sql += "FROM %s AS updatedFeatures GROUP BY %s"%(sql_filtered_feature_table_2, fg.correl_field)
        return [distinctFeatureList, self._executeGetList(sql, False)]

    def makeBinnedOutcomeTable(self, buckets, mid_aom_list):
        """buckets is a list of tuples"""
        raise NotImplementedError

    def getGroupsAndOutcomes(self, groupThresh = 0, lexicon_count_table=None, groupsWhere = ''):
        if groupThresh and self.wordTable != self.get1gramTable():
            _warn("""###################################################################
WARNING: You specified a --word_table and --group_freq_thresh is
enabled, so the total word count for your groups might be off
(remove "--word_table WT" to solve this issue)
###################################################################""")
            
        groups = set()
        outcomes = dict()
        outcomeFieldList = set(self.outcome_value_fields).union(set(self.outcome_controls)).union(set(self.outcome_interaction))
        ocs = dict()
        controls = dict()

        #get outcome values:
        _warn("Loading Outcomes and Getting Groups for: %s" % str(outcomeFieldList)) #debug
        if outcomeFieldList:
            for outcomeField in outcomeFieldList:
                outcomes[outcomeField] = dict(self.getGroupAndOutcomeValues(outcomeField))
                if outcomeField in self.outcome_value_fields:
                    groups.update(outcomes[outcomeField].keys())
            

            if groupThresh:
                where = """ group_id in ('%s')""" % ("','".join(str(g) for g in groups))
                groupCnts = self.getGroupWordCounts(where, lexicon_count_table = lexicon_count_table)
                groups = set()
                for outcomeField, outcomeValues in outcomes.iteritems():
                    newOutcomes = dict()
                    for gId in outcomeValues.iterkeys():
                        if (gId in groupCnts) and (groupCnts[gId] >= groupThresh):
                            #keep
                            # newOutcomes[gId] = float(outcomeValues[gId])
                            newOutcomes[gId] = outcomeValues[gId]
                    outcomes[outcomeField] = newOutcomes
                    if outcomeField in self.outcome_value_fields:
                        groups.update(newOutcomes.keys())

            #set groups:
            for k in self.outcome_controls + self.outcome_interaction:
                groups = groups & set(outcomes[k].keys()) #always intersect with controls
            if groupsWhere:
                outcm = groupsWhere.split('=')[0].strip()
                val = groupsWhere.split('=')[1].strip()
                # print "Maarten getGroupsAndOutcomes", [groupsWhere, outcm, val]
                whereusers = set([i[0] for i in self.getGroupAndOutcomeValues(outcm) if str(i[1]) == val])
                groups = groups & whereusers

            if self.oneGroupSetForAllOutcomes:
                for k in self.outcome_value_fields:
                    groups = groups & set(outcomes[k].keys()) #only intersect if wanting all the same groups
            
            #split into outcomes and controls:
            ocs = dict()
            controls = dict()
            for k in self.outcome_controls + self.outcome_interaction:
                outcomeDict = outcomes[k]
                outcomeDict = dict([(g, v) for g, v in outcomeDict.iteritems() if g in groups])
                controls[k] = outcomeDict
            for k in self.outcome_value_fields:
                outcomeDict = outcomes[k]
                outcomeDict = dict([(g, v) for g, v in outcomeDict.iteritems() if g in groups])
                ocs[k] = outcomeDict
        elif groupThresh:
            groupCnts = self.getGroupWordCounts(where = None, lexicon_count_table = lexicon_count_table)
            groups = set()
            for gId, cnt in groupCnts.iteritems():
                if cnt >= groupThresh:
                    groups.add(gId)
            if groupsWhere:
                outcm = groupsWhere.split('=')[0].strip()
                val = groupsWhere.split('=')[1].strip()
                # print "Maarten getGroupsAndOutcomes", [groupsWhere, outcm, val]
                whereusers = set([i[0] for i in self.getGroupAndOutcomeValues(outcm) if str(i[1]) == val])
                groups = groups & whereusers

        return (groups, ocs, controls)

    def getGroupAndOutcomeValuesAsDF(self, outcomeField = None, where=''):
        """returns a dataframe of (group_id, outcome_value)"""
        if not outcomeField: outcomeField = self.outcome_value_fields[0]
        db_eng = mif.get_db_engine(self.corpdb)
        sql = "select %s, %s from `%s` WHERE %s IS NOT NULL" % (self.correl_field, outcomeField, self.outcome_table, outcomeField)
        if (where): sql += ' WHERE ' + where
        index = self.correl_field
        return pd.read_sql(sql=sql, con=db_eng, index_col=index)

    def getGroupsAndOutcomesAsDF(self, groupThresh = 0, lexicon_count_table=None, groupsWhere = '', sparse=False):
        (groups, allOutcomes, controls) = self.getGroupsAndOutcomes(groupThresh, lexicon_count_table, groupsWhere)
        o_df = pd.DataFrame(allOutcomes)
        c_df = pd.DataFrame(controls)
        if sparse:
            df = pd.concat([o_df, c_df], axis=1).to_sparse(fill_value=0)
            df.index.names = ['group_id']
            return df
        else:
            df = pd.concat([o_df, c_df], axis=1)
            df.index.names = ['group_id']
            return df

    def getAnnotationTableAsDF(self, fields=['unit_id', 'worker_id', 'score'], where='', index=['unit_id', 'worker_id'], pivot=True, fillNA=False):
        """return a dataframe of unit_it, worker_id, score"""
        if fillNA and not pivot:
            _warn("fillNA set to TRUE but pivot set to FALSE. No missing values will be filled.") 
        db_eng = mif.get_db_engine(self.corpdb)
        sql = """SELECT %s, %s, %s from %s""" % tuple(fields + [self.outcome_table])
        if (where): sql += ' WHERE ' + where
        if pivot:
            if fillNA:
                return pd.read_sql(sql=sql, con=db_eng, index_col=index).unstack().fillna(value=0)
            else:
                return pd.read_sql(sql=sql, con=db_eng, index_col=index).unstack()
        else:
            return pd.read_sql(sql=sql, con=db_eng, index_col=index) 
    
    def numGroupsPerOutcome(self, featGetter, outputfile, groupThresh=0, where = ''):
        """prints sas-style csv file output"""
        #get outcome data to work with
        (groups, allOutcomes, controls) = self.getGroupsAndOutcomes(groupThresh)

        #adjust keys for outcomes and controls:
        countGroups = dict()
        for outcomeField, outcomes in allOutcomes.iteritems():
            countGroups[outcomeField] = len(outcomes)

        return countGroups
