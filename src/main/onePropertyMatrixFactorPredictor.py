import fixedValuePredictor
import numpy
import multiprocessing
import copy
import operator
from collections import Counter
    

class OnePropertyMatrixFactorPredictor(fixedValuePredictor.FixedValuePredictor):
    
    def __init__(self):
        # each region has a different vector for each property
        self.property2region2Vector = {}
        self.property2vector = {}
        # keep this as a backup:
        fixedValuePredictor.FixedValuePredictor.__init__(self)
        
    def predict(self, property, region):
        # it can be the case that we haven't got anything for a country
        if property in self.property2vector and region in self.property2region2Vector[property]:
            return numpy.dot(self.property2vector[property], self.property2region2Vector[property][region])
        else:
            print "no vector for property ", property.encode('utf-8'), " or no vector for region ", region.encode('utf-8'), " for this property"
            return fixedValuePredictor.FixedValuePredictor.predict(self, property, region)
        
    def trainRelation(self, d, property, trainMatrix, textMatrix, learningRate, regParam, iterations, filterThreshold, learningRateBalance):
        #property = propertyQueue.get()
        trainRegion2value = trainMatrix[property]
        print property, " training starting now"
        
        # first let's filter
        filteredPatterns = []
        filteredPatternMAPES = []
        lowestNonZeroMAPE = float("inf")
        for pattern, region2value in textMatrix.items():
            # make sure that it has at least two value in common with training data, otherwise we might get spurious stuff
            keysInCommon = list(set(region2value.keys()) & set(trainRegion2value.keys()))
            if len(keysInCommon) > 1:
                #print pattern
                #print region2value
                mape = self.supportScaledMAPE(region2value, trainRegion2value, 1)
                if mape < filterThreshold:
                    filteredPatterns.append(pattern)
                    filteredPatternMAPES.append(mape)
                    if mape < lowestNonZeroMAPE:
                        lowestNonZeroMAPE = mape
                
        print property, ", patterns left after filtering ", len(filteredPatterns)
        if len(filteredPatterns) == 0:
            print property, ", no patterns left after filtering, SKIP"
            return
        
        # ignore the setting, set it according to the text patterns   
        dims = max(2, int(numpy.ceil(numpy.sqrt(len(filteredPatterns)))))
        print property, ", set the dimensions to the square root of the text patterns = ", dims 
    
        #regParam /= numpy.power(dims, 0.1)
        #print property, "set the reg param to ", regParam
    
        # initialize the low dim representations
        # first the property
        propertyVector = numpy.random.rand(dims)
        

        # then the patterns and the regions
        region2Vector = {}            
        pattern2vector = {}
        # also count the times they appear in the patterns
        trainingRegion2counts = Counter()
        valuesPresent = 0
        for pattern in filteredPatterns:
            pattern2vector[pattern] = numpy.random.rand(dims)
            valuesPresent += len(textMatrix[pattern]) 
            for region in textMatrix[pattern].keys():
                if region not in region2Vector:
                    region2Vector[region] =  numpy.random.rand(dims)
                if region in trainRegion2value:
                    trainingRegion2counts[region] += 1 
                    
        
        print property, ", regions after filtering: ", len(region2Vector)
        
        print property, ", values present ", valuesPresent, " density ", float(valuesPresent)/(len(filteredPatterns)*len(region2Vector))
        
        #propertyLearningRate = (float(valuesPresent)/len(trainRegion2value))* learningRate
        # let's go!
        
        allpps = [property] + filteredPatterns
        
        absPropertyMedian = numpy.abs(numpy.median(trainRegion2value.values()))
        for iter in xrange(iterations):
            numpy.random.shuffle(allpps)            
            for pp in allpps:
                # we might be getting the values from either the train matrix or the 
                if pp == property:
                    region2value = trainRegion2value
                else:
                    region2value = textMatrix[pp]
                # let's try to reconstruct each known value    
                regVals = region2value.items()
                numpy.random.shuffle(regVals)
                for region, value in regVals:
                    # we might not have a vector for this region, so ignore
                    if region in region2Vector:
                        # reconstruction error
                        if pp == property:
                            ppVector = propertyVector
                            # +1 is for the cases where we haven't seen this training region with any pattern
                            lr = (learningRateBalance*trainingRegion2counts[region] + 1) * learningRate
                        else:
                            ppVector = pattern2vector[pp]
                            lr = learningRate

                        eij = value - numpy.dot(ppVector,region2Vector[region])
                        # scale it
                        #eij /= medianAbs
                        # kind of APE 
                        #if numpy.abs(value) > 1: 
                        #    eij /= numpy.square(value)
                        #if region in trainRegion2value and not (trainRegion2value[region] == 0):
                        #    eij /= numpy.abs(trainRegion2value[region])
                        #else:
                        #    eij /= absPropertyMedian
                        
                        if numpy.abs(eij) > 1:
                            eij = numpy.sign(eij)
                            
                        ppVector += lr * (2 * eij * region2Vector[region] - regParam * ppVector)
                        region2Vector[region] += lr * (2 * eij * ppVector - regParam * region2Vector[region])
        
            # let's calculate the squared reconstruction error
            # maybe look only at the training data?
            #squaredErrors = []
            absoluteErrors = []
            preds = {}
            for region, value in trainRegion2value.items():
                if region in region2Vector:
                    pred = numpy.dot(propertyVector,region2Vector[region])
                    try:
                        error = pred - value
                        absoluteErrors.append(numpy.absolute(error))
                        #squaredErrors.append(numpy.square(error))
                    except FloatingPointError:
                        print property, ", iteration ", iter, ", error for region ", region.encode('utf-8'), " too big, IGNORED"
                    preds[region] = pred
            #mase = self.MASE(preds, trainRegion2value)
            mape = self.MAPE(preds, trainRegion2value)
            #print property, ", iteration ", iter, " reconstruction mean squared error on trainMatrix=", numpy.mean(squaredErrors)
            print property, ", iteration ", iter, " reconstruction mean absolute error on trainMatrix=", numpy.mean(absoluteErrors)
            #print property, ", iteration ", iter, " MASE on trainMatrix=", mase
            print property, ", iteration ", iter, " MAPE on trainMatrix=", mape

            #patternSquaredErrors = []
            patternAbsoluteErrors = []
            trueVals = {}
            predVals = {}            
            for pattern in filteredPatterns:
                region2value = textMatrix[pattern]
                for region, value in region2value.items():
                    pred = numpy.dot(pattern2vector[pattern],region2Vector[region])
                    error = pred - value
                    patternAbsoluteErrors.append(numpy.absolute(error))
                    trueVals[region+pattern] = value
                    predVals[region+pattern] = pred
            #print property, ", iteration ", iter, " reconstruction mean squared error on textMatrix=", numpy.mean(patternSquaredErrors)
            textMean = numpy.mean(patternAbsoluteErrors)
            print property, ", iteration ", iter, " reconstruction mean absolute error on textMatrix=", textMean 
            patternMape = self.MAPE(predVals, trueVals)
            print property, ", iteration ", iter, " MAPE on textMatrix=", patternMape 
            
            euclidDistanceFromPropertyVector = {}
            pVectorSquare = numpy.dot(propertyVector, propertyVector)
            for pattern, vector in pattern2vector.items():
                # if the distance is too high ignore.
                try:
                    euclidDistanceFromPropertyVector[pattern] = numpy.sqrt(numpy.dot(vector, vector) - 2 * numpy.dot(vector, propertyVector) + pVectorSquare)
                except FloatingPointError:
                    pass
            
            sortedPaterns= sorted(euclidDistanceFromPropertyVector.items(), key=operator.itemgetter(1))
            
            print "top-10 patterns closest to the property in euclidean distance : distance from property "
            for idx in xrange(min(10, len(sortedPaterns))):
                print sortedPaterns[idx][0].encode('utf-8'), ":", sortedPaterns[idx][1]
            
            if mape < 0.000001:
                break
        
        d[property] = (propertyVector, region2Vector)
        #self.property2vector[property] = propertyVector
        #self.property2region2Vector[property] = region2Vector 
        
                    
    
    # parameters are: learning rate, reg_parameter, iterations, filtering threshold
    def train(self, trainMatrix, textMatrix, params=[0.1, 1, 5000, 0.1, 1]):
        # get the back up fixed values
        fixedValuePredictor.FixedValuePredictor.train(self, trainMatrix, textMatrix)
    
        learningRate, regParam, iterations, filterThreshold, learningRateBalance = params                    
        
        mgr = multiprocessing.Manager()
        d = mgr.dict()
         

        # now let's do the MF for each property separately:
        jobs = []
        for property in trainMatrix.keys(): # ["/location/statistical_region/renewable_freshwater_per_capita", "/location/statistical_region/population"]: # ["/location/statistical_region/size_of_armed_forces"]:#    
            #if property in ["/location/statistical_region/fertility_rate"]: # 
            job = multiprocessing.Process(target=self.trainRelation, args=(d, property, trainMatrix, textMatrix, learningRate, regParam, iterations, filterThreshold, learningRateBalance,))
            jobs.append(job)
            #else:
            #    self.property2median[property] = numpy.median(trainMatrix[property].values())
        
        # Start the processes (i.e. calculate the random number lists)        
        for j in jobs:
            j.start()

        # Ensure all of the processes have finished
        for j in jobs:
            j.join()
            
        for property, (propertyVector, region2Vector) in d.items():    
            self.property2region2Vector[property] = copy.copy(region2Vector)
            self.property2vector[property] = copy.copy(propertyVector)
        
        print "Done training"
        
                 
if __name__ == "__main__":
    
    import sys
    # helps detect errors
    numpy.seterr(all='raise')
    # set the random seed for reproducibility
    numpy.random.seed(13)
    
    predictor = OnePropertyMatrixFactorPredictor()
    
    trainMatrix = predictor.loadMatrix(sys.argv[1])
    textMatrix = predictor.loadMatrix(sys.argv[2])
    testMatrix = predictor.loadMatrix(sys.argv[3])
    
    #TODO: These should now be sets of values for these parameters that need to be evaluated
    #TODO: Actually, they should be determined on a per relation basis eventually, let's start with one set though
    learningRate = float(sys.argv[4])
    l2penalty = float(sys.argv[5])
    iterations = int(sys.argv[6])
    filterThreshold = float(sys.argv[7])
    learningRateBalance = float(sys.argv[8])
    
    # TODO: this function should now return the best parameters per relation 
    property2bestParams = OnePropertyMatrixFactorPredictor.crossValidate(trainMatrix, textMatrix, 4, [[learningRate, l2penalty, iterations, filterThreshold, learningRateBalance]])
    predictor.runEval(trainMatrix, textMatrix, testMatrix, property2bestParams)