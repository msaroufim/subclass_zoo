import torch
from torch.testing._internal.common_utils import run_tests, TestCase
from torch.utils._python_dispatch import enable_python_mode

"""
From Christian:

One category is select operators. The most stereotypical example is
nn.Embedding (and historically it was the reason we introduced sparsity). Part
of sparse gradient support is also preventing further spread of the
"sparse_grad" kwarg (e.g. gather
(https://pytorch.org/docs/master/generated/torch.gather.html#torch.gather))
and getting rid of torch.sparse.sum (sometimes sparse grad sometimes not
https://pytorch.org/docs/master/generated/torch.sparse.sum.html#torch.sparse.sum
) or torch.sparse.mm.

The other category are binary ops. This is also where the output layout choice
comes from.

I wrote up an issue overview that categories things
https://docs.google.com/document/d/12wN0RPFoavSxIYtvtRTD5cv0fN1FlRhOkaOAFYCfxEI/edit#
- checkout the section under "mul". There's also
https://github.com/pytorch/pytorch/issues/8853 .
"""


class SparseOutputMode(torch.Tensor):
    @staticmethod
    def __new__(cls, elem):
        raise RuntimeError("this mode mixin cannot actually be instantiated")

    @classmethod
    def __torch_dispatch__(cls, func, types, args=(), kwargs=None):
        if func == torch.ops.aten.mul:
            # TODO: this algorithm is probably not what you actually want to do
            # run the multiply
            r = super().__torch_dispatch__(func, types, args, kwargs)
            # sparsify it
            return r.to_sparse()

        return super().__torch_dispatch__(func, types, args, kwargs)


def sparse_output(func, *args, **kwargs):
    with enable_python_mode(SparseOutputMode):
        return func(*args, **kwargs)


class SparseOutputTest(TestCase):
    def test_mul(self):
        x = torch.randn(3, requires_grad=True)
        y = torch.randn(3, requires_grad=True)
        r = sparse_output(torch.mul, torch.diag(x), torch.diag(y))
        self.assertEqual(
            r,
            torch.sparse_coo_tensor(
                torch.tensor([[0, 1, 2], [0, 1, 2]], dtype=torch.long), x * y
            ),
        )
        # This doesn't work yet because this results in a sparse-dense
        # multiply which is not supported
        # r.values().sum().backward()


if __name__ == "__main__":
    run_tests()
