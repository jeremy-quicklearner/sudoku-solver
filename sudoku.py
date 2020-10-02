#!/usr/bin/python
from __future__ import print_function
from collections import namedtuple
from os import system
from time import sleep
from random import choice

Guess = namedtuple('Guess', ['id', 'n', 'choices'])
Elimination = namedtuple('Elimination', ['id', 'n'])
EliminationChain = namedtuple('EliminationChain', ['guess', 'eliminations'])

eliminate_count = 0
restore_count = 0
guess_count = 0
unguess_count = 0

class Cell(object):
    def __init__(self, id, given=0):
        self.id_ = id
        if given == 0:
            self.couldBe_ = set(range(1,10))
        else:
            self.couldBe_ = set([given])

    def id(self):
        return self.id_

    def couldBe(self):
        # TODO: cache
        return sorted(self.couldBe_)

    def eliminate(self, n):
        global eliminate_count
        if n in self.couldBe_:
            self.couldBe_ -= set([n])
            e = Elimination(self.id_, n)
            eliminate_count += 1
        else:
            e = None
        return e

    def restore(self, e):
        global restore_count
        if e.id != self.id_:
            raise Exception('Can\'t restore %s to cell %s as it was eliminated from cell %s' % (e.n, self.id_, e.id))
        if e.n in self.couldBe_:
            raise Exception('Can\'t restore %s to cell %s as it is already a possibility' % (e.n, e.id))
        restore_count += 1
        self.couldBe_ = self.couldBe_.union(set([e.n]))

    def guess(self):
        global guess_count
        n = min(self.couldBe())
        g = Guess(self.id_, n, self.couldBe_)
        self.couldBe_ = set([n])
        guess_count += 1
        return g

    def unguess(self, g):
        global unguess_count
        if g.id != self.id_:
            raise Exception('Can\'t unguess %s to cell %s as it was guessed in cell %s' % (g.n, self.id_, g.id))
        self.couldBe_ = g.choices
        unguess_count += 1
        return self.eliminate(g.n)

class Group(object):
    def __init__(self, cells):
        if len(cells) != 9:
            raise Exception('Illegal group size %d' % len(cells))
        self.cells_ = cells

    def reduce(self):
        #TODO: Better algorithm with pairs, triples, etc. Hard!
        eliminations = []
        for cell in self.cells_:
            if len(cell.couldBe()) == 1:
                val = cell.couldBe()[0]
                for otherCell in self.cells_:
                    if otherCell == cell:
                        continue
                    e = otherCell.eliminate(val)
                    if e:
                        eliminations.append(e)
        return eliminations

class Grid(object):
    def __init__(self, givens):
        self.cells_ = [ None for i in range(0, 9 * 9)]
        givensById = {g.id() : g for g in givens}

        for i in range(0,9 * 9):
            if i in givensById:
                self.cells_[i] = givensById[i]
            else:
                self.cells_[i] = Cell(i)

    def __str__(self):
        raster = '\033[32m#########################################################################\n\033[0m'
        for row in range(0,9):
            for subrow in [0,1,2]:
                raster += '\033[32m#\033[0m '
                for col in range(0,9):
                    cb = self.cells_[row * 9 + col].couldBe()
                    for subcol in [1,2,3]:
                        n = subrow * 3 + subcol
                        if n in cb:
                            raster += str(n)
                        else:
                            raster += ' '
                        raster += ' '
                    if col % 3 == 2:
                        raster += '\033[32m#\033[0m '
                    else:
                        raster += '\033[32m|\033[0m '
                raster += '\n'
            if row % 3 == 2:
                raster += '\033[32m#########################################################################\033[0m\n'
            else:
                raster += '\033[32m#-------+-------+-------#-------+-------+-------#-------+-------+-------#\033[0m\n'
        return raster

    # TODO: CACHE
    def row(self, idx):
        if idx not in range(0,9):
            raise Exception('Illegal row index %s' % idx)
        cells = []
        for col in range(0,9):
            cells.append(self.cells_[idx * 9 + col])
        return Group(cells)
    def rows(self):
        res = []
        for idx in range(0,9):
            res.append(self.row(idx))
        return res
    
    def col(self, idx):
        if idx not in range(0,9):
            raise Exception('Illegal column index %s' % idx)
        cells = []
        for row in range(0,9):
            cells.append(self.cells_[row * 9 + idx])
        return Group(cells)
    def cols(self):
        res = []
        for idx in range(0,9):
            res.append(self.col(idx))
        return res
    
    def box(self, idx):
        if idx not in range(0,9):
            raise Exception('Illegal box index %s' % idx)
        cells = []
        for subidx in range(0,9):
            row = (idx / 3) * 3 + (subidx / 3)
            col = (idx % 3) * 3 + (subidx % 3)
            cells.append(self.cells_[row * 9 + col])
        return Group(cells)
    def boxes(self):
        res = []
        for idx in range(0,9):
            res.append(self.box(idx))
        return res

    def groups(self):
        return self.rows() + self.cols() + self.boxes()

    def cellToGuess(self):
        bestCell = self.cells_[0]
        bestLen = len(bestCell.couldBe())
        for cell in self.cells_:
            thisLen = len(cell.couldBe())
            if thisLen == 2:
                return cell
            if thisLen == 1:
                continue
            if bestLen == 1 or thisLen < bestLen:
                bestCell = cell
                bestLen = thisLen
        return bestCell

    def contradictory(self):
        for cell in self.cells_:
            if len(cell.couldBe()) == 0:
                return True
        return False

    def solved(self):
        for cell in self.cells_:
            if len(cell.couldBe()) != 1:
                return False
        return True

    def backtrack(self, chain):
        for e in chain.eliminations:
            self.cells_[e.id].restore(e)
        return self.cells_[chain.guess.id].unguess(chain.guess)

def arr2grid(arr):
    cells = []
    for i in range(0,9):
        for j in range(0,9):
            if arr[i][j] not in range(0,10):
                raise Exception('Illegal given %d' % arr[i][j])
            if arr[i][j] != 0:
                cells.append(Cell(i * 9 + j, arr[i][j]))
    return Grid(cells)

g = arr2grid([
    [8,0,0, 0,0,0, 0,0,0],
    [0,0,3, 6,0,0, 0,0,0],
    [0,7,0, 0,9,0, 2,0,0],

    [0,5,0, 0,0,7, 0,0,0],
    [0,0,0, 0,4,5, 7,0,0],
    [0,0,0, 1,0,0, 0,3,0],

    [0,0,1, 0,0,0, 0,6,8],
    [0,0,8, 5,0,0, 0,1,0],
    [0,9,0, 0,0,0, 4,0,0]
])

system('clear')
print(g)
eliminationChains = [EliminationChain(None,[])]

while not g.solved():
    if g.contradictory():
        if len(eliminationChains) == 1:
            raise Exception('Puzzle has no solution')
        eliminatedByGuess = g.backtrack(eliminationChains.pop())
        eliminationChains[-1].eliminations.append(eliminatedByGuess)

    eliminationsFromReduction = []
    for group in g.groups():
        print('\033[F' * 45, end='\r')
        print(g)
        print('Guesses: %d (%d correct, %d backtracked)' % (guess_count, guess_count - unguess_count, unguess_count))
        print('Eliminations: %d (%d correct, %d restored)' % (eliminate_count, eliminate_count - restore_count, restore_count))
        eliminationsFromReduction += group.reduce()

    if eliminationsFromReduction:
        eliminationChains[-1].eliminations.extend(eliminationsFromReduction)
        continue

    eliminationChains.append(EliminationChain(g.cellToGuess().guess(),[]))

raw_input("Solved")
