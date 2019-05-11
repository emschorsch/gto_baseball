from pycallgraph import PyCallGraph
from pycallgraph import Config
from pycallgraph import GlobbingFilter
from pycallgraph.output import GraphvizOutput

from baseball.optimizer import optimizer
from baseball.optimizer import validator

config = Config()
config.trace_filter = GlobbingFilter(include=[
    'baseball.simulator.simulator.*',
    'baseball.optimizer.*',
])

graphviz = GraphvizOutput(output_file='call_graph.png')

with PyCallGraph(output=graphviz, config=config):
    optimizer.optimize('2014', '0904', 3)
    #validator.simulate_year('2014', 100)
