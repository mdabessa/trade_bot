import numpy as np
a = np.arange(10)
a = a.reshape(1, -1)


print(a[np.argmax(a)])
