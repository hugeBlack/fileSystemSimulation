import io
import struct
import math
from collections import deque


class LeafNode:
    def __init__(self, val, ptr):
        self.val = val
        self.ptr = ptr
        self.depth = 0


class TreeNode:
    def __init__(self, leftNode, rightNode):
        self.leftNode = leftNode
        self.rightNode = rightNode
        self.val = (leftNode.val & rightNode.val) if rightNode is not None else leftNode.val
        self.depth = self.leftNode.depth + 1

    def update(self):
        self.val = (self.leftNode.val & self.rightNode.val) if self.rightNode is not None else self.leftNode.val


# bitMapLength: 字节
class BitMapHelper:
    def __init__(self, reader, bitMapStartPtr, bitMapLength):
        self.reader = reader
        self.bitMapStartPtr = bitMapStartPtr
        binQueue = deque()
        self.reader.seek(bitMapStartPtr)
        self.bitMapLength = bitMapLength
        # 叶子节点
        for i in range(0, bitMapLength, 1):
            node = LeafNode(self.reader.read(1)[0], bitMapStartPtr + i)
            binQueue.append(node)

        self.root = binQueue[0]
        while True:
            left = binQueue.popleft()
            self.root = left
            if len(binQueue) <= 0:
                break
            right = None if (binQueue[0].depth != left.depth) else binQueue.popleft()
            node = TreeNode(left, right)
            binQueue.append(node)

    # 找到一个0并反转为1，返回0代表的block
    def allocZero(self):
        if self.root.val == 255:
            return -1

        nowNode = self.root
        nodeStack = deque()
        while type(nowNode) != LeafNode:
            nodeStack.append(nowNode)
            if nowNode.leftNode.val != 255:
                nowNode = nowNode.leftNode
            else:
                nowNode = nowNode.rightNode

        i = 0
        bitMask = 128
        while bitMask > 0:
            if nowNode.val & bitMask == 0:
                nowNode.val |= bitMask
                self.reader.seek(nowNode.ptr)
                self.reader.write(bytes([nowNode.val]))
                break
            bitMask >>= 1
            i += 1

        while len(nodeStack) > 0:
            n = nodeStack.pop()
            n.update()

        return (nowNode.ptr - self.bitMapStartPtr) * 8 + i

    # 如果该位置为1返回True，否则返回False
    def setZero(self, bitId: int):
        byteIndex = math.floor(bitId / 8)
        nowNode = self.root
        nodeStack = deque()
        while type(nowNode) != LeafNode:
            nodeStack.append(nowNode)
            bitMask = 1 << (nowNode.depth - 1)
            if byteIndex & bitMask > 0:
                nowNode = nowNode.rightNode
            else:
                nowNode = nowNode.leftNode
        bitMask = 128 >> (bitId % 8)
        if nowNode.val & bitMask == 0:
            return False
        nowNode.val = nowNode.val & ~bitMask
        self.reader.seek(nowNode.ptr)
        self.reader.write(bytes([nowNode.val]))
        while len(nodeStack) > 0:
            n = nodeStack.pop()
            n.update()
        return True

    def getBitMap(self):
        self.reader.seek(self.bitMapStartPtr)
        return self.reader.read(self.bitMapLength)

    def checkIsFree(self, index: int):
        self.reader.seek(self.bitMapStartPtr + index // 8)
        byte = self.reader.read(1)[0]
        bitMask = 128 >> (index % 8)
        return byte & bitMask == 0


if __name__ == "__main__":
    a = b'\xff\xff\xff\xff\xff'
    bio = io.BytesIO(a)

    bh = BitMapHelper(bio, 0, 5)
    bh.setZero(20)
    print(bh.allocZero())
