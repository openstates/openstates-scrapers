library(wnominate)

args <- commandArgs(TRUE)

inFile <- args[1]
outFile <- args[2]
polarity = c(args[3])

print(polarity)
voteData <- as.matrix(read.csv(inFile, header=FALSE))
names <- voteData[, 1]
legData <- matrix(voteData[, c(2,3)], length(voteData[, 2]), 2)
colnames(legData) <- c("leg_id", "party")
voteData <- voteData[, -(1:3)]

rc <- rollcall(voteData, yea=c(1, 2, 3), nay=c(4, 5, 6),
               missing=c(7, 8, 9), notInLegis=0, legis.names=names,
               legis.data=legData)

result <- wnominate(rc, polarity=polarity, dims=1)

write.csv(result$legislators, outFile)
