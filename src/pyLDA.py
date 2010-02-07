'''
Created on Jan 31, 2010
@author: nrolland
From Gregor Heinrich's most excellent text 'Parameter estimation for text analysis'
'''
 
import sys, getopt
import collections, array, numpy
import random, operator


np = 'numpy' in sys.modules
          
def indice(a):
    if np:
        i =numpy.argmax(a)
    else:        
        for i,val in enumerate(a):
            if val > 0:
                break
    return i
 
def indicenbiggest2(i,val, acc, acc_index):
    ret = acc_index
    if val > acc[0]:
        acc[0] = val
        acc_index[0] = i
    else:
        if len(acc)>1:
            sub = acc[1:]
            sub_index = acc_index[1:]
            subret = indicenbiggest2(i,val, sub,sub_index)
            acc_index[1:] = sub_index[:]
            acc[1:] = sub[:]
    
    return ret
 
def indicenbiggest(ar,n):
    acc = [float('-Infinity') for i in range(min(abs(n),len(ar)))]
    acc_index = [ 0 for i in range(min(abs(n),len(ar)))]
    
    for i, val in enumerate(ar):
        indicenbiggest2(i,val, acc, acc_index)
 
    return acc_index
 
 
def flatten(x):
    result = []
    for el in x:
        #if isinstance(el, (list, tuple)):
        if hasattr(el, "__iter__") and not isinstance(el, basestring):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result
 
def zeros(shape):
    '''
        test  = zeros((2,10))
        print "test", test
        test[0][0] = 1
        print "test", test
        print "test", test[0]
        
        input()        
'''
    if np:
        ret = numpy.zeros(shape)
    else:
        ret = [0]*shape[-1]
        for n_for_dim in reversed(shape[:-1]):
            tret = []
            for i in range(n_for_dim):
                tret.append(ret[:])
            ret= tret
            
    return ret

def multinomial(n_add, param, n_dim = 1):
    #s = sum(param)
    if np:
        if n_dim == 1:
            res = numpy.random.multinomial(n_add, param)
        else:
            res = numpy.random.multinomial(n_add, param, n_dim)            
    else:
        res = []
        cdf = [sum(param[:1+end]) for end in range(len(param))]
        zerosample = [0]*len(param)
        for i_dim in range(n_dim):
            sample = zerosample[:]
            for i_add in range(n_add):
                r = random.random()
                for i_cdf, val_cdf in enumerate(cdf):
                    if r < val_cdf : break
                sample[i_cdf] += 1
            res.append(sample)
    
        if n_dim == 1:
            res = flatten(res)
    return res

 
class BagOfWordDoc(dict):
    '''
A document contains for each term_id, the word count f the term in the document
The vocabulary of the document is all the term_id whose word count is not null
'''
    def __init__(self):
        self._vocabulary = None
        self._wordcount  = None
        self._words = None
    
    def vocabulary(self):
        self._vocabulary = self._vocabulary or self.keys()
        return self._vocabulary
 
    def Nwords(self):
        self._wordcount = self._wordcount or reduce(operator.add, self.values(), 0)
        return self._wordcount
    
    def words(self):
        self._words = self._words or flatten([ [ term_id for i in range(self[term_id]) ]for term_id in self ])
        return self._words
        
class SparseDocCollection(list):
    '''
A class to read collection of documents in a bag of word sparse format:
docword.filename :
M number of docs
V numbers of words in vocabulary
L numbers of (documents, words) occurence that follows
doc_id word_id doc_word_count
vocab.filename:
list of words
'''
    def __init__(self):
        self.vocabulary = []
                
    def write(self, commonfilename, directory="."):
        docfile = file(directory+"/docword." + commonfilename, "w")
        for doc_id, doc in enumerate(self):
            #print "doc_id", doc_id
            for term_id in doc.vocabulary():
                #print "word_id", word_id
                msg = str(doc_id) + "   " + str(term_id) + "  " + str(doc[term_id]) + "\n"
                #print msg
                docfile.write(msg)
        docfile.close()
        vocfile = file(directory+"/vocab." + commonfilename,"w")
        for term_id, term in enumerate(self.vocabulary):
            #print "term_id", term_id
            vocfile.write( str(term_id) +"   " + str(term) )
        vocfile.close()
        
        
    def read(self, commonfilename, directory="."):
        '''
name : common part of the name e.g. xxx for docword.xxx and vocab.xxx
'''
        self.vocabulary = file(directory+"/vocab." + commonfilename).readlines()
        docfile = file(directory+"/docword." + commonfilename)
        self.M=int(docfile.readline()) #doc number
        self.V=int(docfile.readline()) #vocab size
        self.L=int(docfile.readline()) #wordcount
        
        last = -1
        maxterm_id = -1
        minterm_id = +999999999
        for line in docfile.readlines():
            doc_id, term_id, doc_word_count = map(lambda st: int(st), line.split(' '))
            term_id = term_id -1
            if len(self) < doc_id:
                doc = BagOfWordDoc()
                self.append(doc)
            doc = self[-1]
            if maxterm_id < term_id:
                maxterm_id = term_id
            if term_id < minterm_id:
                minterm_id = term_id
            if last != doc_id and doc_id - round(doc_id /1000, 0) *1000 == 0:
                print str((doc_id *100) / self.M) + "%"
                last = doc_id
            doc[term_id] = doc_word_count
        #print "maxterm_id", maxterm_id
        #print "minterm_id", minterm_id
        if maxterm_id - minterm_id + 1 != self.V:
            print "warning"

 
class LDAModel():
    def __init__(self):
        #prior among topic in docs
        self.alpha = 0.5
        #prior among topic in words
        self.beta = 0.5
        self.ntopics = 10
        self.niters = 1000
        
        self.savestep = 50
        self.tsavemostlikelywords = 20
        self.docs = SparseDocCollection()

        
    def load(self):
        self.docs.read('enron.dev.txt','../trainingdocs')
        self.ntopic_by_doc_topic = zeros((len(self.docs), self.ntopics))
        self.ntopic_by_doc       = zeros((len(self.docs), ))
        self.nterm_by_topic_term = zeros((self.ntopics, len(self.docs.vocabulary)))
        self.nterm_by_topic      = zeros((self.ntopics, ))
        self.z_doc_word          = [ zeros((doc.Nwords(), )) for doc in self.docs]

    def test(self):    
        self.docs = SparseDocCollection()
        self.docs.read('enron.dev.txt','../trainingdocs')
        self.docs.write('toto.txt')
        
    def add(self,doc_id, term_id, topic, qtty=1.):
        self.ntopic_by_doc_topic[doc_id][topic] += qtty
        self.ntopic_by_doc      [doc_id]   += qtty             
        self.nterm_by_topic_term[topic][term_id] += qtty
        self.nterm_by_topic     [topic] += qtty
        
    def remove(self, doc_id, term_id, topic):
        self.add(doc_id, term_id, -1.)
    
    def printmostfreqtopic(self):
        ndocs_topics = [0]*self.ntopics            
        for doc_id, doc in enumerate(self.docs):
            for topic in xrange(self.ntopics):
                ndocs_topics[topic] += self.ntopic_by_doc_topic[doc_id][topic]
        print "Most topic among docs :",   sum(ndocs_topics) 
             
    def saveit(self, mfw=False, wordspertopic=False, docspertopic=False):
        if mfw:
            totalfreq = [0]*len(self.docs.vocabulary)
            for doc_id, doc in enumerate(self.docs):
                words = doc.words()
                for term_id in doc.vocabulary():
                    totalfreq[term_id] += doc[term_id]
            print "Most frequent words among docs :",  map(lambda i:self.docs.vocabulary[i],indicenbiggest(totalfreq, self.tsavemostlikelywords))
        if wordspertopic:
            for topic in range(self.ntopics):
                index = indicenbiggest(self.nterm_by_topic_term[topic][:], self.tsavemostlikelywords)
                print "MF word for topic", topic, map(lambda i:self.docs.vocabulary[i],index)
        if docspertopic:
            ndocs_topics = [0]*self.ntopics            
            for doc_id, doc in enumerate(self.docs):
                for topic in range(self.ntopics):
                    ndocs_topics[topic] += self.ntopic_by_doc_topic[doc_id][topic]
            print "Docs per topics :",  "(total)", sum( ndocs_topics), ndocs_topics
    def info(self):
        print "# of documents : ", len(self.docs)
        print "# of terms  : ", len(self.docs.vocabulary)
        print "# of words  : ", sum(map(lambda doc:doc.Nwords(), self.docs))
        print "# of topics:  ", self.ntopics

    def initialize(self):
        self.alphai = self.alpha / self.ntopics
        self.betai  = self.beta / len(self.docs.vocabulary)
        
        model_init = [1. / self.ntopics] *self.ntopics
        print "initial seed"
        for doc_id, doc in enumerate(self.docs):
            topic_for_words = multinomial(1, model_init,doc.Nwords())
            i_word = 0
            for term_id in doc:
                for i_term_occ in xrange(doc[term_id]):
                    i_topic =  indice(topic_for_words[i_word])
                    self.z_doc_word[doc_id][i_word] = i_topic
                    self.add(doc_id, term_id,i_topic)
                    i_word += 1     

    def iterate(self):
        for doc_id, doc in enumerate(self.docs):
            i_word =0 
            #print doc_id
            for  term_id in doc:
                for i_term_occ in xrange(doc[term_id]):
                    self.remove(doc_id, term_id, self.z_doc_word[doc_id][i_word])
                    param = [(self.nterm_by_topic_term[topic][term_id] + self.betai) / ( self.nterm_by_topic[topic] + self.beta) * \
                            ( self.ntopic_by_doc_topic[doc_id][topic] +  self.alphai) / ( self.ntopic_by_doc[doc_id] + self.alpha) for topic in range(self.ntopics)]
                    if np: 
                        param /= numpy.sum(param)
                    else:
                        s = sum(param)
                        param = [param[i] / s for i in range(self.ntopics)]
                    new_topic = multinomial(1, param)
                    self.z_doc_word[doc_id][i_word] = indice(new_topic)
                    self.add(doc_id, term_id, self.z_doc_word[doc_id][i_word])
                    i_word += 1
            if doc_id - (doc_id / 500)*500== 0:
                #saveit()
                print "iter", iter, " doc : ", doc_id ,"/" , len(self.docs)

    def run(self,niters,savestep):
        old_lik = -999999999999


        for iter in range(niters):
            print "iteration #", iter
            if iter - (iter/savestep)*savestep == 0:
                self.saveit(False, True , False)
            
        
        


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "htw", ["help"])
        except getopt.error, msg:
            raise Usage(msg)
        
        for o, a in opts:
            if o in ("-h", "--help"):
                raise Usage(__file__ +' -alpha ')
            if o in ("-t", "--test"):
                print >>sys.stdout, 'TEST MODE'
                test = True
            if o in ("-w", "--write test"):
                print >>sys.stdout, 'TEST MODE'
                test = True
        if len(args)<0 :
            raise Usage("arguments missing")

        model = LDAModel()
        
        model.load()
        model.info()
        model.run(0, 3)
        model.saveit(True, True, True)
        
        print "fin"
        
        
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        return 2
 
 
if __name__ == "__main__":
    sys.exit(main())
 
